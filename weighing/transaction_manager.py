# Transaction Manager - handles transaction lifecycle and state management
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import uuid

from database.data_access import DataAccessLayer
from auth.auth_service import get_auth_service
from auth.rbac import Permission

class TransactionStatus(Enum):
    """Transaction status enumeration"""
    PENDING = "pending"
    COMPLETE = "complete"
    VOID = "void"

class WeighingMode(Enum):
    """Weighing mode enumeration"""
    TWO_PASS = "two_pass"
    FIXED_TARE = "fixed_tare"

@dataclass
class WeighEvent:
    """Represents a single weigh event"""
    sequence: int  # 1 or 2
    weight: float
    is_gross: bool  # True for gross, False for tare
    is_stable: bool
    captured_at: datetime
    raw_payload: str
    photo_path: Optional[str] = None

@dataclass
class Transaction:
    """Represents a weighing transaction"""
    id: str
    ticket_no: int
    vehicle_no: str
    product_id: Optional[str]
    party_id: Optional[str]
    transporter_id: Optional[str]
    do_po_no: Optional[str]
    mode: WeighingMode
    status: TransactionStatus
    net_weight: Optional[float]
    notes: Optional[str]
    operator_open_id: str
    operator_close_id: Optional[str]
    opened_at: datetime
    closed_at: Optional[datetime]
    weigh_events: List[WeighEvent]

class TransactionManager:
    """Manages weighing transactions and their lifecycle"""
    
    def __init__(self, db_manager: DataAccessLayer):
        self.db = db_manager
        self.auth_service = get_auth_service()
        self.stale_hours = 24  # Hours after which pending transaction is considered stale
        
    def start_transaction(
        self, 
        vehicle_no: str, 
        mode: WeighingMode, 
        product_id: str = None,
        party_id: str = None,
        transporter_id: str = None,
        do_po_no: str = None,
        notes: str = None
    ) -> Optional[Transaction]:
        """Start a new weighing transaction"""
        
        # Check permissions
        if not self.auth_service.has_permission(Permission.CREATE_TRANSACTION):
            return None
            
        # Get current user
        user = self.auth_service.get_current_user()
        if not user:
            return None
            
        try:
            # Check for existing pending transaction for this vehicle
            existing = self.get_pending_transaction_by_vehicle(vehicle_no)
            if existing:
                raise ValueError(f"Vehicle {vehicle_no} already has a pending transaction (#{existing.ticket_no})")
                
            # Generate transaction ID and ticket number
            transaction_id = str(uuid.uuid4())
            ticket_no = self.generate_ticket_number()
            
            # Create transaction record
            now = datetime.utcnow()
            
            query = """
                INSERT INTO transactions (
                    id, ticket_no, vehicle_no, product_id, party_id, 
                    transporter_id, do_po_no, mode, status, notes,
                    operator_open_id, opened_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            self.db.execute_insert(query, (
                transaction_id, ticket_no, vehicle_no, product_id, party_id,
                transporter_id, do_po_no, mode.value, TransactionStatus.PENDING.value,
                notes, user['id'], now.isoformat()
            ))
            
            # Log transaction creation
            self.db.log_audit_action(
                operator_id=user['username'],
                action='CREATE_TRANSACTION',
                entity='transactions',
                entity_id=transaction_id,
                reason=f'New {mode.value} transaction started',
                before_state={},
                after_state={
                    'ticket_no': ticket_no,
                    'vehicle_no': vehicle_no,
                    'mode': mode.value,
                    'status': TransactionStatus.PENDING.value
                }
            )
            
            # Create and return Transaction object
            transaction = Transaction(
                id=transaction_id,
                ticket_no=ticket_no,
                vehicle_no=vehicle_no,
                product_id=product_id,
                party_id=party_id,
                transporter_id=transporter_id,
                do_po_no=do_po_no,
                mode=mode,
                status=TransactionStatus.PENDING,
                net_weight=None,
                notes=notes,
                operator_open_id=user['id'],
                operator_close_id=None,
                opened_at=now,
                closed_at=None,
                weigh_events=[]
            )
            
            return transaction
            
        except Exception as e:
            print(f"Error starting transaction: {e}")
            return None
    
    def capture_weight(
        self, 
        transaction_id: str, 
        weight: float, 
        sequence: int,
        is_gross: bool,
        is_stable: bool,
        raw_payload: str = ""
    ) -> bool:
        """Capture a weight reading for a transaction"""
        
        # Check permissions
        if not self.auth_service.has_permission(Permission.CAPTURE_WEIGHT):
            return False
            
        try:
            # Generate weigh event ID
            weigh_event_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            # Insert weigh event
            query = """
                INSERT INTO weigh_events (
                    id, transaction_id, seq, gross_flag, weight, 
                    stable, captured_at_utc, raw_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            self.db.execute_insert(query, (
                weigh_event_id, transaction_id, sequence, int(is_gross),
                weight, int(is_stable), now.isoformat(), raw_payload
            ))
            
            # Log weight capture
            user = self.auth_service.get_current_user()
            self.db.log_audit_action(
                operator_id=user['username'] if user else 'system',
                action='CAPTURE_WEIGHT',
                entity='weigh_events',
                entity_id=weigh_event_id,
                reason=f'Weight captured: sequence {sequence}',
                before_state={},
                after_state={
                    'weight': weight,
                    'sequence': sequence,
                    'stable': is_stable,
                    'gross_flag': is_gross
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Error capturing weight: {e}")
            return False
    
    def complete_transaction(
        self, 
        transaction_id: str,
        net_weight: float = None
    ) -> bool:
        """Complete a transaction and calculate net weight"""
        
        # Check permissions
        if not self.auth_service.has_permission(Permission.CREATE_TRANSACTION):
            return False
            
        try:
            # Get transaction
            transaction = self.get_transaction_by_id(transaction_id)
            if not transaction or transaction.status != TransactionStatus.PENDING:
                return False
                
            # Calculate net weight if not provided
            if net_weight is None:
                net_weight = self.calculate_net_weight(transaction_id)
                
            if net_weight is None:
                return False
                
            # Get current user
            user = self.auth_service.get_current_user()
            if not user:
                return False
                
            # Update transaction status
            now = datetime.utcnow()
            
            query = """
                UPDATE transactions 
                SET status = ?, net_weight = ?, operator_close_id = ?, closed_at_utc = ?
                WHERE id = ?
            """
            
            self.db.execute_insert(query, (
                TransactionStatus.COMPLETE.value,
                net_weight,
                user['id'],
                now.isoformat(),
                transaction_id
            ))
            
            # Log transaction completion
            self.db.log_audit_action(
                operator_id=user['username'],
                action='COMPLETE_TRANSACTION',
                entity='transactions',
                entity_id=transaction_id,
                reason='Transaction completed',
                before_state={'status': 'pending'},
                after_state={
                    'status': 'complete',
                    'net_weight': net_weight,
                    'completed_by': user['username']
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Error completing transaction: {e}")
            return False
    
    def void_transaction(
        self, 
        transaction_id: str, 
        reason: str
    ) -> bool:
        """Void a completed transaction"""
        
        # Check permissions - only Supervisor and Admin can void
        if not self.auth_service.require_permission(Permission.VOID_TRANSACTION):
            return False
            
        if not reason or reason.strip() == "":
            return False
            
        try:
            # Get transaction
            transaction = self.get_transaction_by_id(transaction_id)
            if not transaction or transaction.status == TransactionStatus.VOID:
                return False
                
            # Get current user
            user = self.auth_service.get_current_user()
            if not user:
                return False
                
            # Update transaction status
            query = "UPDATE transactions SET status = ? WHERE id = ?"
            self.db.execute_insert(query, (TransactionStatus.VOID.value, transaction_id))
            
            # Log void action
            self.db.log_audit_action(
                operator_id=user['username'],
                action='VOID_TRANSACTION',
                entity='transactions',
                entity_id=transaction_id,
                reason=reason,
                before_state={
                    'status': transaction.status.value,
                    'net_weight': transaction.net_weight
                },
                after_state={
                    'status': 'void',
                    'voided_by': user['username'],
                    'void_reason': reason
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Error voiding transaction: {e}")
            return False
    
    def calculate_net_weight(self, transaction_id: str) -> Optional[float]:
        """Calculate net weight from weigh events"""
        try:
            # Get weigh events for transaction
            query = """
                SELECT seq, gross_flag, weight 
                FROM weigh_events 
                WHERE transaction_id = ? 
                ORDER BY seq
            """
            
            results = self.db.execute_query(query, (transaction_id,))
            if not results:
                return None
                
            gross_weight = None
            tare_weight = None
            
            for seq, gross_flag, weight in results:
                if gross_flag == 1:  # Gross weight
                    gross_weight = weight
                else:  # Tare weight
                    tare_weight = weight
                    
            # Calculate net weight
            if gross_weight is not None and tare_weight is not None:
                net_weight = abs(gross_weight - tare_weight)
                
                # Apply rounding rules (get from settings)
                # For now, round to 2 decimal places
                return round(net_weight, 2)
                
            return None
            
        except Exception as e:
            print(f"Error calculating net weight: {e}")
            return None
    
    def get_transaction_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """Get transaction by ID"""
        try:
            query = """
                SELECT id, ticket_no, vehicle_no, product_id, party_id,
                       transporter_id, do_po_no, mode, status, net_weight,
                       notes, operator_open_id, operator_close_id,
                       opened_at_utc, closed_at_utc
                FROM transactions 
                WHERE id = ?
            """
            
            result = self.db.execute_query(query, (transaction_id,))
            if not result:
                return None
                
            row = result[0]
            
            # Get weigh events
            weigh_events = self.get_weigh_events(transaction_id)
            
            return Transaction(
                id=row[0],
                ticket_no=row[1],
                vehicle_no=row[2],
                product_id=row[3],
                party_id=row[4],
                transporter_id=row[5],
                do_po_no=row[6],
                mode=WeighingMode(row[7]),
                status=TransactionStatus(row[8]),
                net_weight=row[9],
                notes=row[10],
                operator_open_id=row[11],
                operator_close_id=row[12],
                opened_at=datetime.fromisoformat(row[13]) if row[13] else None,
                closed_at=datetime.fromisoformat(row[14]) if row[14] else None,
                weigh_events=weigh_events
            )
            
        except Exception as e:
            print(f"Error getting transaction: {e}")
            return None
    
    def get_pending_transaction_by_vehicle(self, vehicle_no: str) -> Optional[Transaction]:
        """Get pending transaction for a vehicle"""
        try:
            query = """
                SELECT id FROM transactions 
                WHERE vehicle_no = ? AND status = ?
            """
            
            result = self.db.execute_query(query, (vehicle_no, TransactionStatus.PENDING.value))
            if result:
                return self.get_transaction_by_id(result[0][0])
            return None
            
        except Exception as e:
            print(f"Error getting pending transaction: {e}")
            return None
    
    def get_weigh_events(self, transaction_id: str) -> List[WeighEvent]:
        """Get weigh events for a transaction"""
        try:
            query = """
                SELECT seq, gross_flag, weight, stable, captured_at_utc, raw_payload
                FROM weigh_events 
                WHERE transaction_id = ?
                ORDER BY seq
            """
            
            results = self.db.execute_query(query, (transaction_id,))
            
            events = []
            for row in results:
                events.append(WeighEvent(
                    sequence=row[0],
                    is_gross=bool(row[1]),
                    weight=row[2],
                    is_stable=bool(row[3]),
                    captured_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    raw_payload=row[5] or ""
                ))
                
            return events
            
        except Exception as e:
            print(f"Error getting weigh events: {e}")
            return []
    
    def get_stale_transactions(self) -> List[Transaction]:
        """Get transactions that have been pending for too long"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.stale_hours)
            
            query = """
                SELECT id FROM transactions 
                WHERE status = ? AND opened_at_utc < ?
                ORDER BY opened_at_utc
            """
            
            results = self.db.execute_query(query, (
                TransactionStatus.PENDING.value,
                cutoff_time.isoformat()
            ))
            
            transactions = []
            for row in results:
                transaction = self.get_transaction_by_id(row[0])
                if transaction:
                    transactions.append(transaction)
                    
            return transactions
            
        except Exception as e:
            print(f"Error getting stale transactions: {e}")
            return []
    
    def generate_ticket_number(self) -> int:
        """Generate next ticket number"""
        try:
            # Get the highest ticket number
            query = "SELECT MAX(ticket_no) FROM transactions"
            result = self.db.execute_query(query)
            
            if result and result[0][0] is not None:
                return result[0][0] + 1
            else:
                return 1
                
        except Exception as e:
            print(f"Error generating ticket number: {e}")
            return 1
    
    def get_transactions_by_status(self, status: TransactionStatus) -> List[Transaction]:
        """Get all transactions with specific status"""
        try:
            query = "SELECT id FROM transactions WHERE status = ? ORDER BY ticket_no DESC"
            results = self.db.execute_query(query, (status.value,))
            
            transactions = []
            for row in results:
                transaction = self.get_transaction_by_id(row[0])
                if transaction:
                    transactions.append(transaction)
                    
            return transactions
            
        except Exception as e:
            print(f"Error getting transactions by status: {e}")
            return []
    
    def search_transactions(
        self, 
        vehicle_no: str = None,
        ticket_no: int = None,
        date_from: datetime = None,
        date_to: datetime = None,
        status: TransactionStatus = None
    ) -> List[Transaction]:
        """Search transactions with various criteria"""
        try:
            query = "SELECT id FROM transactions WHERE 1=1"
            params = []
            
            if vehicle_no:
                query += " AND vehicle_no LIKE ?"
                params.append(f"%{vehicle_no}%")
                
            if ticket_no:
                query += " AND ticket_no = ?"
                params.append(ticket_no)
                
            if date_from:
                query += " AND opened_at_utc >= ?"
                params.append(date_from.isoformat())
                
            if date_to:
                query += " AND opened_at_utc <= ?"
                params.append(date_to.isoformat())
                
            if status:
                query += " AND status = ?"
                params.append(status.value)
                
            query += " ORDER BY ticket_no DESC"
            
            results = self.db.execute_query(query, params)
            
            transactions = []
            for row in results:
                transaction = self.get_transaction_by_id(row[0])
                if transaction:
                    transactions.append(transaction)
                    
            return transactions
            
        except Exception as e:
            print(f"Error searching transactions: {e}")
            return []
