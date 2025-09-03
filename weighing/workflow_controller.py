# Workflow Controller - coordinates all weighing operations
from typing import Optional, Dict, Any, Callable, List
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from enum import Enum
from datetime import datetime

from .transaction_manager import TransactionManager, Transaction, WeighingMode
from .weighing_modes import WeighingModeFactory, WeighingModeBase, WeighingStep
from .weight_validator import WeightValidator
from hardware.serial_service import SerialService
from database.data_access import DataAccessLayer
from auth.auth_service import get_auth_service
from auth.rbac import Permission
from core.config import DATABASE_PATH

class WorkflowState(Enum):
    """Overall workflow states"""
    IDLE = "idle"                         # No active transaction
    READY = "ready"                       # Ready to start weighing
    WEIGHING = "weighing"                 # Active weighing process
    WAITING_STABLE = "waiting_stable"     # Waiting for stable weight
    WEIGHT_CAPTURED = "weight_captured"   # Weight successfully captured
    COMPLETED = "completed"               # Transaction completed
    ERROR = "error"                       # Error state

class WorkflowController(QObject):
    """Main controller for weighing workflow operations"""
    
    # Signals
    state_changed = pyqtSignal(str, str)  # old_state, new_state
    weight_updated = pyqtSignal(float, bool)  # weight, is_stable
    weight_captured = pyqtSignal(dict)  # weight_info
    transaction_started = pyqtSignal(dict)  # transaction_info
    transaction_completed = pyqtSignal(dict)  # transaction_info
    step_changed = pyqtSignal(str)  # step_description
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self):
        super().__init__()
        
        # Core components
        self.db_manager = DataAccessLayer(str(DATABASE_PATH))
        self.transaction_manager = TransactionManager(self.db_manager)
        self.weight_validator = WeightValidator()
        self.auth_service = get_auth_service()
        
        # Hardware integration
        self.serial_service: Optional[SerialService] = None
        
        # Current state
        self.current_state = WorkflowState.IDLE
        self.current_mode: Optional[WeighingModeBase] = None
        self.current_transaction: Optional[Transaction] = None
        
        # Weight monitoring
        self.current_weight = 0.0
        self.is_weight_stable = False
        self.last_weight_update = None
        
        # Auto-capture settings
        self.auto_capture_enabled = True
        self.auto_capture_delay = 2.0  # seconds
        self.auto_capture_timer = QTimer()
        self.auto_capture_timer.setSingleShot(True)
        self.auto_capture_timer.timeout.connect(self._auto_capture_weight)
        
        # Periodic tasks
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)  # Update every second
        
        # Initialize validator settings from database
        self._load_validator_settings()
        
    def initialize_hardware(self, serial_service: SerialService):
        """Initialize hardware integration"""
        self.serial_service = serial_service
        
        # Connect to weight updates
        if hasattr(serial_service, 'weight_received'):
            serial_service.weight_received.connect(self._on_weight_received)
            
        if hasattr(serial_service, 'connection_status_changed'):
            serial_service.connection_status_changed.connect(self._on_connection_changed)
    
    def start_weighing(
        self, 
        mode: WeighingMode,
        vehicle_no: str,
        product_id: str = None,
        party_id: str = None,
        transporter_id: str = None,
        do_po_no: str = None,
        notes: str = None,
        fixed_tare: float = None
    ) -> bool:
        """Start weighing process"""
        
        # Check authentication and permissions
        if not self.auth_service.has_permission(Permission.WEIGH_VEHICLE):
            self.error_occurred.emit("Insufficient permissions to start weighing")
            return False
            
        if not vehicle_no or vehicle_no.strip() == "":
            self.error_occurred.emit("Vehicle number is required")
            return False
            
        try:
            # Reset any previous state
            self.reset_workflow()
            
            # Create weighing mode instance
            self.current_mode = WeighingModeFactory.create_mode(mode, self.transaction_manager)
            
            # Start weighing based on mode
            kwargs = {
                'product_id': product_id,
                'party_id': party_id,
                'transporter_id': transporter_id,
                'do_po_no': do_po_no,
                'notes': notes
            }
            
            if mode == WeighingMode.FIXED_TARE and fixed_tare is not None:
                kwargs['fixed_tare'] = fixed_tare
                
            success = self.current_mode.start_weighing(vehicle_no, **kwargs)
            
            if success:
                self.current_transaction = self.current_mode.get_current_transaction()
                self._change_state(WorkflowState.READY)
                
                # Emit transaction started signal
                if self.current_transaction:
                    transaction_info = self._get_transaction_info()
                    self.transaction_started.emit(transaction_info)
                    
                self._update_step_description()
                return True
            else:
                self.error_occurred.emit("Failed to start weighing process")
                return False
                
        except Exception as e:
            self.error_occurred.emit(f"Error starting weighing: {str(e)}")
            return False
    
    def capture_weight_manual(self, weight: float = None) -> bool:
        """Manually capture current weight"""
        
        if not self.auth_service.has_permission(Permission.CAPTURE_WEIGHT):
            self.error_occurred.emit("Insufficient permissions to capture weight")
            return False
            
        if weight is None:
            weight = self.current_weight
            
        return self._capture_weight(weight, self.is_weight_stable)
    
    def void_transaction(self, transaction_id: str, reason: str) -> bool:
        """Void a transaction"""
        
        if not self.auth_service.require_permission(Permission.VOID_TRANSACTION):
            return False
            
        success = self.transaction_manager.void_transaction(transaction_id, reason)
        
        if success:
            # Reset workflow if this was the current transaction
            if self.current_transaction and self.current_transaction.id == transaction_id:
                self.reset_workflow()
                
        return success
    
    def reset_workflow(self):
        """Reset workflow to idle state"""
        self.auto_capture_timer.stop()
        
        if self.current_mode:
            self.current_mode.reset()
            self.current_mode = None
            
        self.current_transaction = None
        self.weight_validator.reset()
        
        self._change_state(WorkflowState.IDLE)
        self.step_changed.emit("Ready to start weighing")
    
    def get_current_state(self) -> WorkflowState:
        """Get current workflow state"""
        return self.current_state
    
    def get_current_transaction(self) -> Optional[Transaction]:
        """Get current transaction"""
        return self.current_transaction
    
    def get_current_weight(self) -> Dict[str, Any]:
        """Get current weight information"""
        return {
            'weight': self.current_weight,
            'is_stable': self.is_weight_stable,
            'validator_status': self.weight_validator.get_stability_status(),
            'last_update': self.last_weight_update.isoformat() if self.last_weight_update else None
        }
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get comprehensive workflow status"""
        status = {
            'state': self.current_state.value,
            'transaction': self._get_transaction_info() if self.current_transaction else None,
            'weight': self.get_current_weight(),
            'step_description': self._get_current_step_description(),
            'can_capture': self._can_capture_weight(),
            'hardware_connected': self._is_hardware_connected()
        }
        
        return status
    
    def _on_weight_received(self, weight_data: Dict[str, Any]):
        """Handle weight received from hardware"""
        try:
            weight = float(weight_data.get('weight', 0))
            is_stable = bool(weight_data.get('stable', False))
            raw_payload = weight_data.get('raw', '')
            
            # Update current weight
            self.current_weight = weight
            self.is_weight_stable = is_stable
            self.last_weight_update = weight_data.get('timestamp')
            
            # Add to validator
            self.weight_validator.add_reading(weight, is_stable, raw_payload)
            
            # Update validator stability
            validator_stable = self.weight_validator.is_weight_stable()
            if validator_stable:
                self.is_weight_stable = True
                
            # Emit weight update signal
            self.weight_updated.emit(weight, self.is_weight_stable)
            
            # Handle auto-capture
            if self.auto_capture_enabled and self._can_capture_weight():
                if self.is_weight_stable:
                    if not self.auto_capture_timer.isActive():
                        self.auto_capture_timer.start(int(self.auto_capture_delay * 1000))
                else:
                    # Weight not stable, cancel auto-capture
                    self.auto_capture_timer.stop()
                    
        except Exception as e:
            print(f"Error processing weight data: {e}")
    
    def _on_connection_changed(self, connected: bool, message: str):
        """Handle hardware connection status change"""
        if not connected:
            self.error_occurred.emit(f"Hardware connection lost: {message}")
        else:
            print(f"Hardware connected: {message}")
    
    def _auto_capture_weight(self):
        """Auto-capture weight when stable"""
        if self._can_capture_weight() and self.is_weight_stable:
            self._capture_weight(self.current_weight, True)
    
    def _capture_weight(self, weight: float, is_stable: bool) -> bool:
        """Internal weight capture method"""
        try:
            if not self.current_mode or not self.current_transaction:
                return False
                
            # Validate weight
            validation = self.weight_validator.validate_weight(weight)
            if not validation['is_valid']:
                error_msg = "; ".join(validation['errors'])
                self.error_occurred.emit(f"Invalid weight: {error_msg}")
                return False
                
            # Get raw payload from last reading
            raw_payload = ""
            if self.weight_validator.reading_history:
                raw_payload = self.weight_validator.reading_history[-1].raw_data
                
            # Capture weight through weighing mode
            success = self.current_mode.capture_weight(weight, is_stable, raw_payload)
            
            if success:
                self._change_state(WorkflowState.WEIGHT_CAPTURED)
                
                # Emit weight captured signal with weight info
                weight_info = {
                    'weight': weight,
                    'stable': is_stable,
                    'timestamp': datetime.now().isoformat(),
                    'raw_payload': raw_payload,
                    'transaction_id': self.current_transaction.id if self.current_transaction else None
                }
                self.weight_captured.emit(weight_info)
                
                # Check if transaction is completed
                current_step = self.current_mode.get_current_step()
                if current_step == WeighingStep.COMPLETED:
                    self._on_transaction_completed()
                else:
                    # Move to next step
                    self._change_state(WorkflowState.READY)
                    
                self._update_step_description()
                return True
            else:
                self.error_occurred.emit("Failed to capture weight")
                return False
                
        except Exception as e:
            self.error_occurred.emit(f"Error capturing weight: {str(e)}")
            return False
    
    def _on_transaction_completed(self):
        """Handle transaction completion"""
        try:
            self._change_state(WorkflowState.COMPLETED)
            
            # Refresh transaction data
            if self.current_transaction:
                refreshed = self.transaction_manager.get_transaction_by_id(self.current_transaction.id)
                if refreshed:
                    self.current_transaction = refreshed
                    
            # Emit completion signal
            transaction_info = self._get_transaction_info()
            self.transaction_completed.emit(transaction_info)
            
            # Auto-reset after a delay (optional)
            # QTimer.singleShot(5000, self.reset_workflow)
            
        except Exception as e:
            self.error_occurred.emit(f"Error completing transaction: {str(e)}")
    
    def _change_state(self, new_state: WorkflowState):
        """Change workflow state"""
        if new_state != self.current_state:
            old_state = self.current_state
            self.current_state = new_state
            self.state_changed.emit(old_state.value, new_state.value)
    
    def _can_capture_weight(self) -> bool:
        """Check if weight can be captured"""
        return (
            self.current_mode is not None and
            self.current_mode.can_capture_weight() and
            self.current_state in [WorkflowState.READY, WorkflowState.WEIGHING]
        )
    
    def _get_current_step_description(self) -> str:
        """Get current step description"""
        if self.current_mode:
            return self.current_mode.get_next_step_description()
        return "No active weighing process"
    
    def _update_step_description(self):
        """Update and emit step description"""
        description = self._get_current_step_description()
        self.step_changed.emit(description)
    
    def _get_transaction_info(self) -> Dict[str, Any]:
        """Get transaction information for signals"""
        if not self.current_transaction:
            return {}
            
        t = self.current_transaction
        return {
            'id': t.id,
            'ticket_no': t.ticket_no,
            'vehicle_no': t.vehicle_no,
            'mode': t.mode.value,
            'status': t.status.value,
            'net_weight': t.net_weight,
            'opened_at': t.opened_at.isoformat() if t.opened_at else None,
            'closed_at': t.closed_at.isoformat() if t.closed_at else None,
            'weigh_events': len(t.weigh_events)
        }
    
    def _is_hardware_connected(self) -> bool:
        """Check if hardware is connected"""
        if self.serial_service:
            return getattr(self.serial_service, 'is_connected', False)
        return False
    
    def _load_validator_settings(self):
        """Load weight validator settings from database"""
        try:
            # Load settings from database
            settings_query = "SELECT key, value FROM settings WHERE key LIKE 'weight_validator_%'"
            results = self.db_manager.execute_query(settings_query)
            
            settings = {}
            for key, value in results:
                settings[key] = float(value) if value.replace('.', '').isdigit() else value
                
            # Apply settings
            self.weight_validator.configure(
                min_weight=settings.get('weight_validator_min_weight', 0.0),
                max_weight=settings.get('weight_validator_max_weight', 100000.0),
                stability_threshold=settings.get('weight_validator_stability_threshold', 5.0),
                stability_duration=settings.get('weight_validator_stability_duration', 3.0)
            )
            
        except Exception as e:
            print(f"Error loading validator settings: {e}")
            # Use default settings
    
    def _update_status(self):
        """Periodic status update"""
        try:
            # Update session activity
            self.auth_service.update_activity()
            
            # Check for stale transactions
            stale_transactions = self.transaction_manager.get_stale_transactions()
            if stale_transactions:
                # Could emit a signal for UI notification
                pass
                
        except Exception as e:
            print(f"Error in status update: {e}")
    
    def configure_auto_capture(self, enabled: bool, delay: float = 2.0):
        """Configure auto-capture settings"""
        self.auto_capture_enabled = enabled
        self.auto_capture_delay = delay
        
        if not enabled:
            self.auto_capture_timer.stop()
    
    def get_stale_transactions(self) -> List[Transaction]:
        """Get stale (pending too long) transactions"""
        return self.transaction_manager.get_stale_transactions()
    
    def search_transactions(self, **criteria) -> List[Transaction]:
        """Search transactions"""
        return self.transaction_manager.search_transactions(**criteria)
