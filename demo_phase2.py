#!/usr/bin/env python3
"""
SCALE System Phase 2 Demo

Demonstrates:
- Authentication system (login, roles, permissions)
- Weighing workflow (two-pass and fixed-tare modes)
- Transaction management
- Weight validation
- Hardware simulation

This demo shows the complete Phase 2 functionality including:
1. User authentication with different roles
2. Starting weighing transactions
3. Weight capture and validation
4. Transaction completion
5. Void functionality (for supervisors)
6. Session management

Author: MiniMax Agent
Date: 2025-08-23
"""

import sys
import time
import random
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

# Add the scale_system path
sys.path.insert(0, '.')

from scale_system.database.data_access import DataAccessLayer
from scale_system.auth import get_auth_service, AuthenticationService
from scale_system.weighing import (
    TransactionManager, WeighingMode, WorkflowController, 
    WorkflowState, WeightValidator
)
from scale_system.hardware.serial_service import SerialService
from scale_system.ui.login_dialog import show_login_dialog

class WeightSimulator(QObject):
    """Simulates weight readings from scale hardware"""
    
    weight_received = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self._generate_weight)
        self.base_weight = 0.0
        self.is_stable = False
        self.noise_level = 5.0
        self.stability_counter = 0
        
    def start_simulation(self, base_weight: float = 0.0):
        """Start weight simulation"""
        self.base_weight = base_weight
        self.timer.start(500)  # Update every 500ms
        
    def stop_simulation(self):
        """Stop weight simulation"""
        self.timer.stop()
        
    def set_weight(self, weight: float, stable: bool = False):
        """Set simulated weight"""
        self.base_weight = weight
        self.is_stable = stable
        self.stability_counter = 10 if stable else 0
        
    def _generate_weight(self):
        """Generate simulated weight reading"""
        # Add some random noise
        noise = random.uniform(-self.noise_level, self.noise_level)
        current_weight = max(0, self.base_weight + noise)
        
        # Determine stability (stable after several consistent readings)
        if abs(noise) < 2.0:
            self.stability_counter += 1
        else:
            self.stability_counter = 0
            
        is_stable = self.stability_counter >= 6
        
        # Emit weight data
        weight_data = {
            'weight': round(current_weight, 1),
            'stable': is_stable,
            'raw': f"ST,GS,{current_weight:.1f},kg",
            'timestamp': datetime.utcnow()
        }
        
        self.weight_received.emit(weight_data)

def print_banner(title: str, width: int = 80):
    """Print a decorative banner"""
    print("\n" + "=" * width)
    print(f"{title:^{width}}")
    print("=" * width)

def print_section(title: str, width: int = 60):
    """Print a section header"""
    print(f"\n{'-' * width}")
    print(f"{title:^{width}}")
    print(f"{'-' * width}")

def simulate_delay(seconds: float, message: str = None):
    """Simulate processing delay with message"""
    if message:
        print(f"\n{message}")
    
    for i in range(int(seconds)):
        print(".", end="", flush=True)
        time.sleep(1)
    print(" Done!")

def demo_authentication():
    """Demonstrate authentication system"""
    print_section("AUTHENTICATION SYSTEM DEMO")
    
    auth_service = get_auth_service()
    
    print("\nAvailable default users:")
    print("- admin / 1234 (Admin role)")
    print("- supervisor / 2345 (Supervisor role)")
    print("- operator / 3456 (Operator role)")
    
    # Test different user roles
    test_users = [
        ('operator', '3456', 'Operator'),
        ('supervisor', '2345', 'Supervisor'),
        ('admin', '1234', 'Admin')
    ]
    
    for username, pin, expected_role in test_users:
        print(f"\nTesting login: {username} (Expected role: {expected_role})")
        
        success = auth_service.authenticate(username, pin)
        
        if success:
            current_user = auth_service.get_current_user()
            print(f"✓ Login successful: {current_user['username']} ({current_user['role']})")
            
            # Test permissions
            features = auth_service.get_accessible_features()
            print(f"  Available features: {len(sum(features.values(), []))} total")
            
            # Test specific actions
            actions_to_test = ['weigh_in', 'void_transaction', 'manage_users']
            for action in actions_to_test:
                can_perform = auth_service.can_perform_action(current_user['role'], action)
                status = "✓ Yes" if can_perform else "✗ No"
                print(f"  Can {action}: {status}")
                
        else:
            print(f"✗ Login failed")
            
        auth_service.logout()
        simulate_delay(1, "Logging out...")
    
    return auth_service

def demo_weighing_workflow(auth_service: AuthenticationService):
    """Demonstrate weighing workflow"""
    print_section("WEIGHING WORKFLOW DEMO")
    
    # Login as operator for weighing
    print("\nLogging in as operator...")
    auth_service.authenticate('operator', '3456')
    
    # Initialize components
    db_manager = DataAccessLayer()
    workflow = WorkflowController()
    weight_sim = WeightSimulator()
    
    # Connect weight simulator to workflow
    weight_sim.weight_received.connect(workflow._on_weight_received)
    
    # Set up workflow signals
    def on_transaction_started(info):
        print(f"\n✓ Transaction started: #{info['ticket_no']} for vehicle {info['vehicle_no']}")
        
    def on_weight_updated(weight, stable):
        status = "STABLE" if stable else "FLUCTUATING"
        print(f"\rWeight: {weight:7.1f} kg ({status})", end="", flush=True)
        
    def on_step_changed(description):
        print(f"\n📋 {description}")
        
    def on_transaction_completed(info):
        print(f"\n✓ Transaction #{info['ticket_no']} completed!")
        print(f"   Net weight: {info['net_weight']} kg")
        
    def on_error(error):
        print(f"\n❌ Error: {error}")
        
    workflow.transaction_started.connect(on_transaction_started)
    workflow.weight_updated.connect(on_weight_updated)
    workflow.step_changed.connect(on_step_changed)
    workflow.transaction_completed.connect(on_transaction_completed)
    workflow.error_occurred.connect(on_error)
    
    # Demo Two-Pass Weighing
    print("\n--- Two-Pass Weighing Demo ---")
    
    # Start transaction
    vehicle_no = "ABC-1234"
    success = workflow.start_weighing(
        mode=WeighingMode.TWO_PASS,
        vehicle_no=vehicle_no,
        product_id="COAL",
        party_id="CUSTOMER_001"
    )
    
    if success:
        # Simulate first weigh (TARE - empty vehicle)
        print("\nStep 1: TARE weighing (empty vehicle)")
        weight_sim.start_simulation()
        
        simulate_delay(2, "Vehicle positioning on scale...")
        weight_sim.set_weight(2500.0, stable=True)  # 2.5 tons empty
        
        simulate_delay(3, "Waiting for stable weight...")
        
        # Manual capture
        workflow.capture_weight_manual()
        
        simulate_delay(1, "Weight captured, vehicle leaving scale...")
        weight_sim.set_weight(0.0)
        
        # Simulate loading/unloading delay
        simulate_delay(3, "Vehicle loading/unloading...")
        
        # Step 2: GROSS weighing (loaded vehicle)
        print("\nStep 2: GROSS weighing (loaded vehicle)")
        
        simulate_delay(2, "Vehicle returning to scale...")
        weight_sim.set_weight(8750.0, stable=True)  # 8.75 tons loaded
        
        simulate_delay(3, "Waiting for stable weight...")
        
        # Manual capture
        workflow.capture_weight_manual()
        
        simulate_delay(1, "Transaction processing...")
        
        # Get final transaction
        final_transaction = workflow.get_current_transaction()
        if final_transaction:
            print(f"\n🎉 Two-pass weighing completed!")
            print(f"   Vehicle: {final_transaction.vehicle_no}")
            print(f"   Ticket #: {final_transaction.ticket_no}")
            print(f"   Tare: {[e.weight for e in final_transaction.weigh_events if not e.is_gross][0]:.1f} kg")
            print(f"   Gross: {[e.weight for e in final_transaction.weigh_events if e.is_gross][0]:.1f} kg")
            print(f"   Net: {final_transaction.net_weight:.1f} kg")
        
        weight_sim.stop_simulation()
        workflow.reset_workflow()
    
    # Demo Fixed-Tare Weighing
    print("\n--- Fixed-Tare Weighing Demo ---")
    
    # Set up fixed tare for a vehicle
    vehicle_no2 = "XYZ-5678"
    
    # Create fixed-tare weighing mode to set tare
    from scale_system.weighing.weighing_modes import FixedTareWeighing
    fixed_tare_mode = FixedTareWeighing(workflow.transaction_manager)
    fixed_tare_mode.set_vehicle_fixed_tare(vehicle_no2, 3200.0)  # 3.2 tons fixed tare
    
    print(f"\nSet fixed tare for vehicle {vehicle_no2}: 3200.0 kg")
    
    # Start fixed-tare transaction
    success = workflow.start_weighing(
        mode=WeighingMode.FIXED_TARE,
        vehicle_no=vehicle_no2,
        product_id="SAND",
        party_id="CUSTOMER_002"
    )
    
    if success:
        print("\nSingle weigh: GROSS weight capture")
        weight_sim.start_simulation()
        
        simulate_delay(2, "Vehicle positioning on scale...")
        weight_sim.set_weight(7800.0, stable=True)  # 7.8 tons gross
        
        simulate_delay(3, "Waiting for stable weight...")
        
        # Manual capture
        workflow.capture_weight_manual()
        
        simulate_delay(1, "Transaction processing...")
        
        # Get final transaction
        final_transaction = workflow.get_current_transaction()
        if final_transaction:
            print(f"\n🎉 Fixed-tare weighing completed!")
            print(f"   Vehicle: {final_transaction.vehicle_no}")
            print(f"   Ticket #: {final_transaction.ticket_no}")
            print(f"   Fixed Tare: 3200.0 kg")
            print(f"   Gross: {[e.weight for e in final_transaction.weigh_events if e.is_gross][0]:.1f} kg")
            print(f"   Net: {final_transaction.net_weight:.1f} kg")
        
        weight_sim.stop_simulation()
        workflow.reset_workflow()
    
    return workflow

def demo_void_transaction(auth_service: AuthenticationService, workflow: WorkflowController):
    """Demonstrate transaction voiding (Supervisor privilege)"""
    print_section("TRANSACTION VOID DEMO")
    
    # Get a completed transaction to void
    transaction_manager = workflow.transaction_manager
    from scale_system.weighing.transaction_manager import TransactionStatus
    
    completed_transactions = transaction_manager.get_transactions_by_status(TransactionStatus.COMPLETE)
    
    if not completed_transactions:
        print("❌ No completed transactions found to void")
        return
        
    transaction_to_void = completed_transactions[0]
    
    print(f"\nFound transaction to void: #{transaction_to_void.ticket_no} ({transaction_to_void.vehicle_no})")
    
    # Try as operator (should fail)
    print("\n1. Attempting void as Operator (should fail)...")
    auth_service.logout()
    auth_service.authenticate('operator', '3456')
    
    success = workflow.void_transaction(transaction_to_void.id, "Test void - insufficient permissions")
    print(f"   Result: {'✓ Success' if success else '✗ Failed (as expected)'}")
    
    # Try as supervisor (should succeed)
    print("\n2. Attempting void as Supervisor (should succeed)...")
    auth_service.logout()
    auth_service.authenticate('supervisor', '2345')
    
    success = workflow.void_transaction(transaction_to_void.id, "Test void by supervisor - demo purposes")
    print(f"   Result: {'✓ Success' if success else '✗ Failed'}")
    
    if success:
        print(f"   Transaction #{transaction_to_void.ticket_no} has been voided")
        
        # Verify void in database
        refreshed = transaction_manager.get_transaction_by_id(transaction_to_void.id)
        if refreshed:
            print(f"   Status updated to: {refreshed.status.value}")

def demo_session_management(auth_service: AuthenticationService):
    """Demonstrate session management"""
    print_section("SESSION MANAGEMENT DEMO")
    
    # Login and get session info
    print("\nLogging in as admin...")
    auth_service.authenticate('admin', '1234')
    
    session_info = auth_service.get_session_info()
    print(f"\nSession Information:")
    print(f"  User: {session_info['username']} ({session_info.get('role', 'Unknown')})")
    print(f"  Login time: {session_info.get('login_time', 'Unknown')}")
    print(f"  Session expires: {session_info.get('session_expires', 'Unknown')}")
    print(f"  Time remaining: {session_info.get('time_remaining', 'Unknown')}")
    
    # Test session validity
    print(f"\nSession valid: {'✓ Yes' if auth_service.is_authenticated() else '✗ No'}")
    
    # Update activity
    simulate_delay(2, "Simulating user activity...")
    auth_service.update_activity()
    
    updated_info = auth_service.get_session_info()
    print(f"Activity updated: {updated_info.get('last_activity', 'Unknown')}")
    
    # Extend session
    print("\nExtending session...")
    auth_service.extend_session()
    
    extended_info = auth_service.get_session_info()
    print(f"Session extended: {extended_info.get('session_expires', 'Unknown')}")
    
    # Logout
    print("\nLogging out...")
    auth_service.logout()
    
    print(f"Session valid after logout: {'✓ Yes' if auth_service.is_authenticated() else '✗ No'}")

def main():
    """Main demo function"""
    
    print_banner("SCALE SYSTEM - PHASE 2 DEMO", 80)
    print("Demonstrating Authentication & Weighing Workflow")
    print(f"Demo started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Create Qt application for signal handling
        app = QApplication(sys.argv)
        
        # Demo 1: Authentication System
        auth_service = demo_authentication()
        
        # Demo 2: Weighing Workflow
        workflow = demo_weighing_workflow(auth_service)
        
        # Demo 3: Transaction Voiding
        demo_void_transaction(auth_service, workflow)
        
        # Demo 4: Session Management
        demo_session_management(auth_service)
        
        print_banner("PHASE 2 DEMO COMPLETED SUCCESSFULLY!", 80)
        
        print("\n🎉 All Phase 2 features demonstrated:")
        print("   ✓ Authentication system with role-based access control")
        print("   ✓ Two-pass weighing workflow")
        print("   ✓ Fixed-tare weighing workflow")
        print("   ✓ Weight validation and stability detection")
        print("   ✓ Transaction management (create, complete, void)")
        print("   ✓ Session management with timeouts")
        print("   ✓ Permission-based operation control")
        print("   ✓ Hardware simulation and integration")
        
        print("\n📋 Next Phase: UI/UX Development")
        print("   - Main weighing screen with PyQt6")
        print("   - Interactive controls and indicators")
        print("   - Real-time weight display")
        print("   - Transaction history and reports")
        
        print(f"\nDemo completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
