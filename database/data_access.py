#!/usr/bin/env python3
"""
SCALE System Data Access Layer
Provides high-level database operations with proper error handling and transactions
"""

import sqlite3
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib

@dataclass
class Transaction:
    """Transaction data class"""
    id: str
    ticket_no: int
    vehicle_no: str
    product_id: Optional[str] = None
    party_id: Optional[str] = None
    transporter_id: Optional[str] = None
    do_po_no: Optional[str] = None
    mode: str = 'two_pass'
    status: str = 'pending'
    net_weight: Optional[float] = None
    notes: Optional[str] = None
    operator_open_id: str = None
    operator_close_id: Optional[str] = None
    opened_at_utc: str = None
    closed_at_utc: Optional[str] = None
    voided_at_utc: Optional[str] = None
    void_reason: Optional[str] = None

@dataclass
class WeighEvent:
    """Weigh event data class"""
    id: str
    transaction_id: str
    seq: int
    gross_flag: int
    weight: float
    stable: int
    captured_at_utc: str
    raw_payload: Optional[str] = None
    photo_path: Optional[str] = None

class DataAccessLayer:
    """Main data access layer for SCALE system"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_connection()
    
    def _ensure_connection(self):
        """Ensure database connection is properly configured"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper configuration"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def create_transaction(self, vehicle_no: str, mode: str, operator_id: str, 
                          product_id: Optional[str] = None, party_id: Optional[str] = None,
                          transporter_id: Optional[str] = None, do_po_no: Optional[str] = None,
                          notes: Optional[str] = None) -> str:
        """Create a new transaction"""
        
        with self.get_connection() as conn:
            # Check if vehicle already has pending transaction
            existing = conn.execute(
                "SELECT id FROM transactions WHERE vehicle_no = ? AND status = 'pending'",
                (vehicle_no,)
            ).fetchone()
            
            if existing:
                raise ValueError(f"Vehicle {vehicle_no} already has a pending transaction")
            
            # Get next ticket number
            ticket_no = self._get_next_ticket_number(conn)
            
            # Create transaction
            transaction_id = str(uuid.uuid4())
            current_time = datetime.utcnow().isoformat()
            
            conn.execute("""
                INSERT INTO transactions 
                (id, ticket_no, vehicle_no, product_id, party_id, transporter_id, 
                 do_po_no, mode, status, notes, operator_open_id, opened_at_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
            """, (transaction_id, ticket_no, vehicle_no, product_id, party_id, 
                  transporter_id, do_po_no, mode, notes, operator_id, current_time))
            
            # Log audit trail
            self._create_audit_log(conn, operator_id, 'CREATE_TRANSACTION', 'transactions', 
                                 transaction_id, 'New transaction created', None, {
                                     'ticket_no': ticket_no,
                                     'vehicle_no': vehicle_no,
                                     'mode': mode
                                 })
            
            conn.commit()
            return transaction_id
    
    def add_weigh_event(self, transaction_id: str, seq: int, weight: float, 
                       stable: bool, raw_payload: Optional[str] = None) -> str:
        """Add a weigh event to a transaction"""
        
        with self.get_connection() as conn:
            # Verify transaction exists and is pending
            transaction = conn.execute(
                "SELECT status FROM transactions WHERE id = ?",
                (transaction_id,)
            ).fetchone()
            
            if not transaction:
                raise ValueError(f"Transaction {transaction_id} not found")
            
            if transaction['status'] != 'pending':
                raise ValueError(f"Transaction {transaction_id} is not pending")
            
            # Check if this sequence already exists
            existing = conn.execute(
                "SELECT id FROM weigh_events WHERE transaction_id = ? AND seq = ?",
                (transaction_id, seq)
            ).fetchone()
            
            if existing:
                raise ValueError(f"Weigh event sequence {seq} already exists for this transaction")
            
            # Create weigh event
            event_id = str(uuid.uuid4())
            current_time = datetime.utcnow().isoformat()
            
            # Determine gross_flag based on sequence and mode
            gross_flag = 1 if seq == 1 else 0  # First weigh is gross, second is tare
            
            conn.execute("""
                INSERT INTO weigh_events 
                (id, transaction_id, seq, gross_flag, weight, stable, captured_at_utc, raw_payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (event_id, transaction_id, seq, gross_flag, weight, 
                  1 if stable else 0, current_time, raw_payload))
            
            conn.commit()
            return event_id
    
    def complete_transaction(self, transaction_id: str, operator_id: str) -> bool:
        """Complete a transaction by calculating net weight"""
        
        with self.get_connection() as conn:
            # Get transaction and weigh events
            transaction = conn.execute(
                "SELECT * FROM transactions WHERE id = ? AND status = 'pending'",
                (transaction_id,)
            ).fetchone()
            
            if not transaction:
                raise ValueError("Transaction not found or not pending")
            
            # Get weigh events
            events = conn.execute(
                "SELECT * FROM weigh_events WHERE transaction_id = ? ORDER BY seq",
                (transaction_id,)
            ).fetchall()
            
            if transaction['mode'] == 'two_pass':
                if len(events) < 2:
                    raise ValueError("Two-pass mode requires both weigh events")
                
                # Calculate net weight (gross - tare)
                gross_weight = events[0]['weight']
                tare_weight = events[1]['weight']
                net_weight = gross_weight - tare_weight
                
            elif transaction['mode'] == 'fixed_tare':
                if len(events) < 1:
                    raise ValueError("Fixed-tare mode requires at least one weigh event")
                
                # Get fixed tare from vehicle
                vehicle = conn.execute(
                    "SELECT fixed_tare FROM vehicles WHERE vehicle_no = ?",
                    (transaction['vehicle_no'],)
                ).fetchone()
                
                if not vehicle or vehicle['fixed_tare'] is None:
                    raise ValueError(f"No fixed tare found for vehicle {transaction['vehicle_no']}")
                
                # Calculate net weight
                gross_weight = events[0]['weight']
                net_weight = gross_weight - vehicle['fixed_tare']
            
            # Apply rounding rules
            net_weight = self._apply_rounding(conn, net_weight)
            
            # Update transaction
            current_time = datetime.utcnow().isoformat()
            
            conn.execute("""
                UPDATE transactions 
                SET status = 'complete', net_weight = ?, operator_close_id = ?, closed_at_utc = ?
                WHERE id = ?
            """, (net_weight, operator_id, current_time, transaction_id))
            
            # Log audit trail
            self._create_audit_log(conn, operator_id, 'COMPLETE_TRANSACTION', 'transactions',
                                 transaction_id, 'Transaction completed', 
                                 {'status': 'pending'}, {'status': 'complete', 'net_weight': net_weight})
            
            conn.commit()
            return True
    
    def void_transaction(self, transaction_id: str, operator_id: str, reason: str) -> bool:
        """Void a completed transaction"""
        
        with self.get_connection() as conn:
            # Get transaction
            transaction = conn.execute(
                "SELECT * FROM transactions WHERE id = ? AND status = 'complete'",
                (transaction_id,)
            ).fetchone()
            
            if not transaction:
                raise ValueError("Transaction not found or not completed")
            
            # Update transaction
            current_time = datetime.utcnow().isoformat()
            
            conn.execute("""
                UPDATE transactions 
                SET status = 'void', voided_at_utc = ?, void_reason = ?
                WHERE id = ?
            """, (current_time, reason, transaction_id))
            
            # Log audit trail
            self._create_audit_log(conn, operator_id, 'VOID_TRANSACTION', 'transactions',
                                 transaction_id, reason, 
                                 {'status': 'complete'}, {'status': 'void'})
            
            conn.commit()
            return True
    
    def get_pending_transactions(self) -> List[Dict]:
        """Get all pending transactions"""
        
        with self.get_connection() as conn:
            transactions = conn.execute("""
                SELECT t.*, u.username as operator_name,
                       p.name as product_name,
                       pt.name as party_name,
                       tr.name as transporter_name
                FROM transactions t
                LEFT JOIN users u ON t.operator_open_id = u.id
                LEFT JOIN products p ON t.product_id = p.id
                LEFT JOIN parties pt ON t.party_id = pt.id
                LEFT JOIN transporters tr ON t.transporter_id = tr.id
                WHERE t.status = 'pending'
                ORDER BY t.opened_at_utc
            """).fetchall()
            
            return [dict(row) for row in transactions]
    
    def get_stale_pending_transactions(self, hours: int = 24) -> List[Dict]:
        """Get pending transactions older than specified hours"""
        
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        with self.get_connection() as conn:
            transactions = conn.execute("""
                SELECT t.*, u.username as operator_name
                FROM transactions t
                LEFT JOIN users u ON t.operator_open_id = u.id
                WHERE t.status = 'pending' AND t.opened_at_utc < ?
                ORDER BY t.opened_at_utc
            """, (cutoff_time,)).fetchall()
            
            return [dict(row) for row in transactions]
    
    def get_transaction_by_vehicle(self, vehicle_no: str) -> Optional[Dict]:
        """Get pending transaction for a vehicle"""
        
        with self.get_connection() as conn:
            transaction = conn.execute("""
                SELECT t.*, u.username as operator_name
                FROM transactions t
                LEFT JOIN users u ON t.operator_open_id = u.id
                WHERE t.vehicle_no = ? AND t.status = 'pending'
            """, (vehicle_no,)).fetchone()
            
            return dict(transaction) if transaction else None
    
    def authenticate_user(self, username: str, pin: Optional[str] = None) -> Optional[Dict]:
        """Authenticate user by username and optional PIN"""
        
        with self.get_connection() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username = ? AND is_active = 1",
                (username,)
            ).fetchone()
            
            if not user:
                return None
            
            # If PIN is provided, verify it
            if pin is not None and user['pin_hash']:
                pin_hash = hashlib.sha256(pin.encode()).hexdigest()
                if pin_hash != user['pin_hash']:
                    return None
            
            return dict(user)
    
    def get_setting(self, key: str) -> Optional[Any]:
        """Get a setting value with type conversion"""
        
        with self.get_connection() as conn:
            setting = conn.execute(
                "SELECT value, data_type FROM settings WHERE key = ?",
                (key,)
            ).fetchone()
            
            if not setting:
                return None
            
            value = setting['value']
            data_type = setting['data_type']
            
            # Convert based on data type
            if data_type == 'integer':
                return int(value)
            elif data_type == 'float':
                return float(value)
            elif data_type == 'boolean':
                return value.lower() in ('1', 'true', 'yes')
            else:
                return value
    
    def set_setting(self, key: str, value: Any, operator_id: str) -> bool:
        """Update a setting value"""
        
        with self.get_connection() as conn:
            current_time = datetime.utcnow().isoformat()
            
            # Get current value for audit
            current = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,)
            ).fetchone()
            
            # Update or insert setting
            conn.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at_utc, updated_by)
                VALUES (?, ?, ?, ?)
            """, (key, str(value), current_time, operator_id))
            
            # Log audit trail
            self._create_audit_log(conn, operator_id, 'UPDATE_SETTING', 'settings',
                                 key, f'Setting {key} updated',
                                 {'value': current['value'] if current else None},
                                 {'value': str(value)})
            
            conn.commit()
            return True
    
    def _get_next_ticket_number(self, conn: sqlite3.Connection) -> int:
        """Get the next ticket number in sequence"""
        
        # Get current max ticket number
        result = conn.execute("SELECT MAX(ticket_no) FROM transactions").fetchone()
        max_ticket = result[0] if result and result[0] else 0
        
        return max_ticket + 1
    
    def _apply_rounding(self, conn: sqlite3.Connection, weight: float) -> float:
        """Apply rounding rules to weight"""
        
        decimal_places = self.get_setting('weight_decimal_places') or 2
        return round(weight, decimal_places)
    
    def _create_audit_log(self, conn: sqlite3.Connection, operator_id: str, 
                         action: str, entity: str, entity_id: str, reason: str,
                         before_state: Optional[Dict], after_state: Optional[Dict]) -> str:
        """Create an audit log entry"""
        
        log_id = str(uuid.uuid4())
        current_time = datetime.utcnow().isoformat()
        
        conn.execute("""
            INSERT INTO audit_log 
            (id, operator_id, action, entity, entity_id, reason, before_state, after_state, logged_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (log_id, operator_id, action, entity, entity_id, reason,
              json.dumps(before_state) if before_state else None,
              json.dumps(after_state) if after_state else None,
              current_time))
        
        return log_id
    
    def create_backup(self, backup_path: str) -> bool:
        """Create database backup"""
        
        try:
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            return True
        except Exception as e:
            print(f"Backup failed: {e}")
            return False
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        
        try:
            with sqlite3.connect(backup_path) as source:
                with sqlite3.connect(self.db_path) as target:
                    source.backup(target)
            return True
        except Exception as e:
            print(f"Restore failed: {e}")
            return False
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """Execute a SELECT query and return results as list of dictionaries"""
        with self.get_connection() as conn:
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_insert(self, query: str, params: Optional[tuple] = None) -> int:
        """Execute an INSERT query and return the last row id"""
        with self.get_connection() as conn:
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)
            conn.commit()
            return cursor.lastrowid
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """Execute an UPDATE/DELETE query and return the number of affected rows"""
        with self.get_connection() as conn:
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)
            conn.commit()
            return cursor.rowcount
    
    def close(self):
        """Close database connections. Using context managers, so this is a no-op."""
        # No persistent connection to close since we use context managers
        pass
    
    def log_audit_action(self, operator_id: str, action: str, entity: str,
                        entity_id: str, reason: str = None, 
                        before_state: dict = None, after_state: dict = None) -> str:
        """Log audit action (public method for compatibility)"""
        with self.get_connection() as conn:
            return self._create_audit_log(conn, operator_id, action, entity, 
                                        entity_id, reason, before_state, after_state)


if __name__ == "__main__":
    # Test data access layer
    dal = DataAccessLayer("../data/scale_system.db")
    
    # Test authentication
    user = dal.authenticate_user("admin")
    if user:
        print(f"Authenticated user: {user['username']} ({user['role']})")
    
    # Test settings
    port = dal.get_setting('serial_port')
    print(f"Serial port setting: {port}")
    
    # Get pending transactions
    pending = dal.get_pending_transactions()
    print(f"Pending transactions: {len(pending)}")
