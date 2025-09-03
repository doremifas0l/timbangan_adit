# Weighing modes implementation
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum

from .transaction_manager import TransactionManager, WeighingMode, Transaction
from database.data_access import DataAccessLayer

class WeighingStep(Enum):
    """Weighing process steps"""
    READY = "ready"                   # Ready to start
    FIRST_WEIGH = "first_weigh"       # First weight capture (Tare or Gross)
    SECOND_WEIGH = "second_weigh"     # Second weight capture (Gross or Tare)
    COMPLETED = "completed"           # Transaction completed

class WeighingModeBase(ABC):
    """Base class for weighing modes"""
    
    def __init__(self, transaction_manager: TransactionManager):
        self.transaction_manager = transaction_manager
        self.current_step = WeighingStep.READY
        self.current_transaction: Optional[Transaction] = None
        
    @abstractmethod
    def start_weighing(self, vehicle_no: str, **kwargs) -> bool:
        """Start weighing process"""
        pass
        
    @abstractmethod
    def capture_weight(self, weight: float, is_stable: bool, raw_payload: str = "") -> bool:
        """Capture weight reading"""
        pass
        
    @abstractmethod
    def get_next_step_description(self) -> str:
        """Get description of next required step"""
        pass
        
    @abstractmethod
    def can_capture_weight(self) -> bool:
        """Check if system is ready to capture weight"""
        pass
        
    def get_current_step(self) -> WeighingStep:
        """Get current weighing step"""
        return self.current_step
        
    def get_current_transaction(self) -> Optional[Transaction]:
        """Get current transaction"""
        return self.current_transaction
        
    def reset(self):
        """Reset weighing mode to initial state"""
        self.current_step = WeighingStep.READY
        self.current_transaction = None

class TwoPassWeighing(WeighingModeBase):
    """Two-pass weighing mode implementation
    
    Process:
    1. First weigh (Tare) - Vehicle enters empty
    2. Second weigh (Gross) - Vehicle exits loaded/unloaded
    3. Calculate net weight (Gross - Tare)
    """
    
    def start_weighing(
        self, 
        vehicle_no: str, 
        product_id: str = None,
        party_id: str = None,
        transporter_id: str = None,
        do_po_no: str = None,
        notes: str = None
    ) -> bool:
        """Start two-pass weighing transaction"""
        
        # Check if vehicle already has pending transaction
        existing = self.transaction_manager.get_pending_transaction_by_vehicle(vehicle_no)
        if existing:
            # Resume existing transaction
            self.current_transaction = existing
            
            # Determine current step based on weigh events
            events = existing.weigh_events
            if not events:
                self.current_step = WeighingStep.FIRST_WEIGH
            elif len(events) == 1:
                self.current_step = WeighingStep.SECOND_WEIGH
            else:
                self.current_step = WeighingStep.COMPLETED
                
            return True
            
        # Create new transaction
        transaction = self.transaction_manager.start_transaction(
            vehicle_no=vehicle_no,
            mode=WeighingMode.TWO_PASS,
            product_id=product_id,
            party_id=party_id,
            transporter_id=transporter_id,
            do_po_no=do_po_no,
            notes=notes
        )
        
        if transaction:
            self.current_transaction = transaction
            self.current_step = WeighingStep.FIRST_WEIGH
            return True
            
        return False
        
    def capture_weight(self, weight: float, is_stable: bool, raw_payload: str = "") -> bool:
        """Capture weight for two-pass weighing"""
        
        if not self.can_capture_weight():
            return False
            
        if not self.current_transaction:
            return False
            
        transaction_id = self.current_transaction.id
        
        if self.current_step == WeighingStep.FIRST_WEIGH:
            # First weigh - typically TARE (empty vehicle)
            success = self.transaction_manager.capture_weight(
                transaction_id=transaction_id,
                weight=weight,
                sequence=1,
                is_gross=False,  # Tare weight
                is_stable=is_stable,
                raw_payload=raw_payload
            )
            
            if success:
                self.current_step = WeighingStep.SECOND_WEIGH
                return True
                
        elif self.current_step == WeighingStep.SECOND_WEIGH:
            # Second weigh - GROSS (loaded vehicle)
            success = self.transaction_manager.capture_weight(
                transaction_id=transaction_id,
                weight=weight,
                sequence=2,
                is_gross=True,  # Gross weight
                is_stable=is_stable,
                raw_payload=raw_payload
            )
            
            if success:
                # Complete transaction
                if self.transaction_manager.complete_transaction(transaction_id):
                    self.current_step = WeighingStep.COMPLETED
                    return True
                    
        return False
        
    def get_next_step_description(self) -> str:
        """Get description of next step"""
        if self.current_step == WeighingStep.READY:
            return "Ready to start weighing. Enter vehicle number and details."
        elif self.current_step == WeighingStep.FIRST_WEIGH:
            return "TARE WEIGHING: Position empty vehicle on scale and capture weight."
        elif self.current_step == WeighingStep.SECOND_WEIGH:
            return "GROSS WEIGHING: Position loaded vehicle on scale and capture weight."
        elif self.current_step == WeighingStep.COMPLETED:
            return "Transaction completed. Net weight calculated."
        else:
            return "Unknown step"
            
    def can_capture_weight(self) -> bool:
        """Check if ready to capture weight"""
        return self.current_step in [WeighingStep.FIRST_WEIGH, WeighingStep.SECOND_WEIGH]

class FixedTareWeighing(WeighingModeBase):
    """Fixed-tare weighing mode implementation
    
    Process:
    1. Use pre-stored tare weight for vehicle
    2. Single weigh (Gross) - Vehicle on scale
    3. Calculate net weight (Gross - Fixed Tare)
    """
    
    def start_weighing(
        self, 
        vehicle_no: str, 
        product_id: str = None,
        party_id: str = None,
        transporter_id: str = None,
        do_po_no: str = None,
        notes: str = None,
        fixed_tare: float = None
    ) -> bool:
        """Start fixed-tare weighing transaction"""
        
        # Get fixed tare weight for vehicle
        if fixed_tare is None:
            fixed_tare = self.get_vehicle_fixed_tare(vehicle_no)
            
        if fixed_tare is None or fixed_tare <= 0:
            print(f"No valid fixed tare weight found for vehicle {vehicle_no}")
            return False
            
        # Check if vehicle already has pending transaction
        existing = self.transaction_manager.get_pending_transaction_by_vehicle(vehicle_no)
        if existing:
            self.current_transaction = existing
            
            # Determine current step
            events = existing.weigh_events
            if not events:
                self.current_step = WeighingStep.FIRST_WEIGH
            else:
                self.current_step = WeighingStep.COMPLETED
                
            return True
            
        # Create new transaction
        transaction = self.transaction_manager.start_transaction(
            vehicle_no=vehicle_no,
            mode=WeighingMode.FIXED_TARE,
            product_id=product_id,
            party_id=party_id,
            transporter_id=transporter_id,
            do_po_no=do_po_no,
            notes=notes
        )
        
        if transaction:
            self.current_transaction = transaction
            self.current_step = WeighingStep.FIRST_WEIGH
            
            # Store fixed tare as a "weigh event" with sequence 0
            # This helps with calculations later
            self.transaction_manager.capture_weight(
                transaction_id=transaction.id,
                weight=fixed_tare,
                sequence=0,  # Special sequence for fixed tare
                is_gross=False,  # Tare weight
                is_stable=True,  # Fixed tares are always "stable"
                raw_payload=f"FIXED_TARE:{fixed_tare}"
            )
            
            return True
            
        return False
        
    def capture_weight(self, weight: float, is_stable: bool, raw_payload: str = "") -> bool:
        """Capture weight for fixed-tare weighing"""
        
        if not self.can_capture_weight():
            return False
            
        if not self.current_transaction:
            return False
            
        transaction_id = self.current_transaction.id
        
        if self.current_step == WeighingStep.FIRST_WEIGH:
            # Single weigh - GROSS weight
            success = self.transaction_manager.capture_weight(
                transaction_id=transaction_id,
                weight=weight,
                sequence=1,
                is_gross=True,  # Gross weight
                is_stable=is_stable,
                raw_payload=raw_payload
            )
            
            if success:
                # Complete transaction immediately
                if self.transaction_manager.complete_transaction(transaction_id):
                    self.current_step = WeighingStep.COMPLETED
                    return True
                    
        return False
        
    def get_next_step_description(self) -> str:
        """Get description of next step"""
        if self.current_step == WeighingStep.READY:
            return "Ready to start weighing. Enter vehicle number and confirm fixed tare."
        elif self.current_step == WeighingStep.FIRST_WEIGH:
            return "GROSS WEIGHING: Position vehicle on scale and capture weight."
        elif self.current_step == WeighingStep.COMPLETED:
            return "Transaction completed. Net weight calculated using fixed tare."
        else:
            return "Unknown step"
            
    def can_capture_weight(self) -> bool:
        """Check if ready to capture weight"""
        return self.current_step == WeighingStep.FIRST_WEIGH
        
    def get_vehicle_fixed_tare(self, vehicle_no: str) -> Optional[float]:
        """Get fixed tare weight for vehicle from database"""
        try:
            db = self.transaction_manager.db
            query = "SELECT fixed_tare FROM vehicles WHERE vehicle_no = ?"
            result = db.execute_query(query, (vehicle_no,))
            
            if result and result[0][0] is not None:
                return float(result[0][0])
            return None
            
        except Exception as e:
            print(f"Error getting fixed tare for vehicle {vehicle_no}: {e}")
            return None
            
    def set_vehicle_fixed_tare(self, vehicle_no: str, tare_weight: float) -> bool:
        """Set fixed tare weight for vehicle"""
        try:
            db = self.transaction_manager.db
            
            # Insert or update vehicle record
            query = """
                INSERT OR REPLACE INTO vehicles (vehicle_no, fixed_tare, updated_at_utc)
                VALUES (?, ?, ?)
            """
            
            from datetime import datetime
            db.execute_insert(query, (
                vehicle_no, 
                tare_weight, 
                datetime.utcnow().isoformat()
            ))
            
            return True
            
        except Exception as e:
            print(f"Error setting fixed tare for vehicle {vehicle_no}: {e}")
            return False

class WeighingModeFactory:
    """Factory for creating weighing mode instances"""
    
    @staticmethod
    def create_mode(mode: WeighingMode, transaction_manager: TransactionManager) -> WeighingModeBase:
        """Create weighing mode instance"""
        if mode == WeighingMode.TWO_PASS:
            return TwoPassWeighing(transaction_manager)
        elif mode == WeighingMode.FIXED_TARE:
            return FixedTareWeighing(transaction_manager)
        else:
            raise ValueError(f"Unknown weighing mode: {mode}")
