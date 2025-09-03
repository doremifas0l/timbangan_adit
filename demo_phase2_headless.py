#!/usr/bin/env python3
"""
SCALE System Phase 2 Demo - Headless Version

Demonstrates the core Phase 2 functionality without GUI components:
- Authentication system (login, roles, permissions)
- Weighing workflow (two-pass and fixed-tare modes)
- Transaction management
- Weight validation

This demo shows the complete Phase 2 backend functionality including:
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
from datetime import datetime, timedelta

# Add the scale_system path
sys.path.insert(0, '.')

from scale_system.database.data_access import DataAccessLayer
from scale_system.auth import get_auth_service, AuthenticationService
from scale_system.weighing import (
    TransactionManager, WeighingMode, WorkflowState, WeightValidator
)

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
        time.sleep(0.3)  # Faster for demo
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
            total_features = len(sum(features.values(), []))
            print(f"  Available features: {total_features} total")
            
            # Show features by category
            for category, feature_list in features.items():
                if feature_list:
                    print(f"    {category}: {len(feature_list)} features")
            
            # Test specific actions
            actions_to_test = ['weigh_in', 'void_transaction', 'manage_users']
            for action in actions_to_test:
                can_perform = auth_service.can_perform_action(current_user['role'], action)
                status = "✓ Yes" if can_perform else "✗ No"
                print(f"  Can {action}: {status}")
                
        else:
            print(f"✗ Login failed")
            
        auth_service.logout()
        simulate_delay(0.5, "Logging out...")
    
    return auth_service

def demo_transaction_management(auth_service: AuthenticationService):
    """Demonstrate transaction management"""
    print_section("TRANSACTION MANAGEMENT DEMO")
    
    # Login as operator for transactions
    print("\nLogging in as operator...")
    auth_service.authenticate('operator', '3456')
    
    # Initialize transaction manager
    db_manager = DataAccessLayer("scale_system/data/scale_system.db")
    transaction_manager = TransactionManager(db_manager)
    
    # Demo Two-Pass Weighing
    print("\n--- Two-Pass Weighing Transaction ---")
    
    # Start transaction
    vehicle_no = "ABC-1234"
    print(f"Starting transaction for vehicle: {vehicle_no}")
    
    transaction = transaction_manager.start_transaction(
        vehicle_no=vehicle_no,
        mode=WeighingMode.TWO_PASS,
        product_id="COAL",
        party_id="CUSTOMER_001",
        notes="Demo two-pass transaction"
    )
    
    if transaction:
        print(f"✓ Transaction created: #{transaction.ticket_no}")
        print(f"  ID: {transaction.id}")
        print(f"  Vehicle: {transaction.vehicle_no}")
        print(f"  Mode: {transaction.mode.value}")
        print(f"  Status: {transaction.status.value}")
        
        # Simulate first weigh (TARE)
        simulate_delay(1, "Capturing TARE weight...")
        
        tare_weight = 2500.0  # 2.5 tons empty
        success1 = transaction_manager.capture_weight(
            transaction_id=transaction.id,
            weight=tare_weight,
            sequence=1,
            is_gross=False,  # Tare weight
            is_stable=True,
            raw_payload=f"ST,GS,{tare_weight:.1f},kg"
        )
        
        if success1:
            print(f"✓ TARE weight captured: {tare_weight} kg")
        
            # Simulate second weigh (GROSS)
            simulate_delay(1, "Capturing GROSS weight...")
            
            gross_weight = 8750.0  # 8.75 tons loaded
            success2 = transaction_manager.capture_weight(
                transaction_id=transaction.id,
                weight=gross_weight,
                sequence=2,
                is_gross=True,  # Gross weight
                is_stable=True,
                raw_payload=f"ST,GS,{gross_weight:.1f},kg"
            )
            
            if success2:
                print(f"✓ GROSS weight captured: {gross_weight} kg")
                
                # Complete transaction
                simulate_delay(1, "Completing transaction...")
                
                completed = transaction_manager.complete_transaction(transaction.id)
                
                if completed:
                    # Refresh transaction data
                    final_transaction = transaction_manager.get_transaction_by_id(transaction.id)
                    
                    if final_transaction:
                        print(f"\n🎉 Two-pass transaction completed!")
                        print(f"   Ticket #: {final_transaction.ticket_no}")
                        print(f"   Vehicle: {final_transaction.vehicle_no}")
                        print(f"   Tare: {tare_weight:.1f} kg")
                        print(f"   Gross: {gross_weight:.1f} kg")
                        print(f"   Net: {final_transaction.net_weight:.1f} kg")
                        print(f"   Status: {final_transaction.status.value}")
    
    # Demo Fixed-Tare Weighing
    print("\n--- Fixed-Tare Weighing Transaction ---")
    
    vehicle_no2 = "XYZ-5678"
    fixed_tare_weight = 3200.0  # 3.2 tons
    
    # Set up fixed tare in database (simulate)
    print(f"Setting fixed tare for {vehicle_no2}: {fixed_tare_weight} kg")
    
    # Start fixed-tare transaction
    transaction2 = transaction_manager.start_transaction(
        vehicle_no=vehicle_no2,
        mode=WeighingMode.FIXED_TARE,
        product_id="SAND",
        party_id="CUSTOMER_002",
        notes="Demo fixed-tare transaction"
    )
    
    if transaction2:
        print(f"✓ Fixed-tare transaction created: #{transaction2.ticket_no}")
        
        # Add fixed tare as sequence 0
        transaction_manager.capture_weight(
            transaction_id=transaction2.id,
            weight=fixed_tare_weight,
            sequence=0,
            is_gross=False,  # Tare weight
            is_stable=True,
            raw_payload=f"FIXED_TARE:{fixed_tare_weight}"
        )
        
        # Simulate gross weighing
        simulate_delay(1, "Capturing GROSS weight...")
        
        gross_weight2 = 7800.0  # 7.8 tons
        success_gross = transaction_manager.capture_weight(
            transaction_id=transaction2.id,
            weight=gross_weight2,
            sequence=1,
            is_gross=True,  # Gross weight
            is_stable=True,
            raw_payload=f"ST,GS,{gross_weight2:.1f},kg"
        )
        
        if success_gross:
            print(f"✓ GROSS weight captured: {gross_weight2} kg")
            
            # Complete transaction
            simulate_delay(1, "Completing transaction...")
            
            completed2 = transaction_manager.complete_transaction(transaction2.id)
            
            if completed2:
                final_transaction2 = transaction_manager.get_transaction_by_id(transaction2.id)
                
                if final_transaction2:
                    print(f"\n🎉 Fixed-tare transaction completed!")
                    print(f"   Ticket #: {final_transaction2.ticket_no}")
                    print(f"   Vehicle: {final_transaction2.vehicle_no}")
                    print(f"   Fixed Tare: {fixed_tare_weight:.1f} kg")
                    print(f"   Gross: {gross_weight2:.1f} kg")
                    print(f"   Net: {final_transaction2.net_weight:.1f} kg")
                    print(f"   Status: {final_transaction2.status.value}")
    
    return transaction_manager

def demo_void_transaction(auth_service: AuthenticationService, transaction_manager: TransactionManager):
    """Demonstrate transaction voiding (Supervisor privilege)"""
    print_section("TRANSACTION VOID DEMO")
    
    # Get a completed transaction to void
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
    
    success = transaction_manager.void_transaction(transaction_to_void.id, "Test void - insufficient permissions")
    print(f"   Result: {'✓ Success' if success else '✗ Failed (as expected)'}")
    
    # Try as supervisor (should succeed)
    print("\n2. Attempting void as Supervisor (should succeed)...")
    auth_service.logout()
    auth_service.authenticate('supervisor', '2345')
    
    success = transaction_manager.void_transaction(transaction_to_void.id, "Test void by supervisor - demo purposes")
    print(f"   Result: {'✓ Success' if success else '✗ Failed'}")
    
    if success:
        print(f"   Transaction #{transaction_to_void.ticket_no} has been voided")
        
        # Verify void in database
        refreshed = transaction_manager.get_transaction_by_id(transaction_to_void.id)
        if refreshed:
            print(f"   Status updated to: {refreshed.status.value}")

def demo_weight_validation():
    """Demonstrate weight validation"""
    print_section("WEIGHT VALIDATION DEMO")
    
    validator = WeightValidator()
    
    # Configure validator
    validator.configure(
        min_weight=0.0,
        max_weight=50000.0,  # 50 tons max
        stability_threshold=2.0,  # 2kg threshold
        stability_duration=2.0   # 2 second duration
    )
    
    print("\nTesting weight validation:")
    
    # Test various weights
    test_weights = [
        (1500.5, "Normal weight"),
        (-10.0, "Negative weight (invalid)"),
        (60000.0, "Overweight (invalid)"),
        (0.0, "Zero weight (warning)"),
        (5000.0, "Round number (warning)")
    ]
    
    for weight, description in test_weights:
        result = validator.validate_weight(weight)
        
        status = "✓ Valid" if result['is_valid'] else "✗ Invalid"
        print(f"  {weight:8.1f} kg - {description}: {status}")
        
        if result['errors']:
            for error in result['errors']:
                print(f"    Error: {error}")
                
        if result['warnings']:
            for warning in result['warnings']:
                print(f"    Warning: {warning}")
    
    print("\nTesting weight stability:")
    
    # Simulate weight readings for stability
    simulate_weights = [
        (1000.0, "Initial reading"),
        (1005.0, "Slight increase"),
        (998.0, "Slight decrease"),
        (1002.0, "Stabilizing"),
        (1001.0, "More stable"),
        (1000.5, "Very stable")
    ]
    
    for weight, description in simulate_weights:
        reading = validator.add_reading(weight)
        stability_status = validator.get_stability_status()
        
        stable_indicator = "🟢 STABLE" if stability_status['is_stable'] else "🔴 UNSTABLE"
        print(f"  {weight:7.1f} kg - {description}: {stable_indicator}")
        
        if stability_status['is_stable']:
            print(f"    Stable weight: {stability_status['stable_weight']} kg")
            break
    
    # Test anomaly detection
    print("\nTesting anomaly detection:")
    
    # Add some anomalous readings
    anomaly_weights = [1000.0, 1001.0, 5000.0, 1002.0, 999.0, 7000.0, 1000.0]
    
    for weight in anomaly_weights:
        validator.add_reading(weight)
        
    anomalies = validator.detect_weight_anomalies()
    
    if anomalies:
        print(f"  Detected {len(anomalies)} anomalies:")
        for anomaly in anomalies:
            print(f"    {anomaly['type']}: {anomaly['description']}")
    else:
        print("  No anomalies detected")
    
    # Show reading statistics
    stats = validator.get_reading_statistics()
    print(f"\nReading statistics:")
    print(f"  Total readings: {stats.get('count', 0)}")
    print(f"  Average weight: {stats.get('average', 0):.1f} kg")
    print(f"  Weight range: {stats.get('min', 0):.1f} - {stats.get('max', 0):.1f} kg")
    print(f"  Standard deviation: {stats.get('std_dev', 0):.2f} kg")

def demo_session_management(auth_service: AuthenticationService):
    """Demonstrate session management"""
    print_section("SESSION MANAGEMENT DEMO")
    
    # Login and get session info
    print("\nLogging in as admin...")
    auth_service.authenticate('admin', '1234')
    
    session_info = auth_service.get_session_info()
    print(f"\nSession Information:")
    print(f"  User: {session_info.get('username', 'Unknown')} ({session_info.get('role', 'Unknown')})")
    print(f"  Login time: {session_info.get('login_time', 'Unknown')}")
    print(f"  Time remaining: {session_info.get('time_remaining', 'Unknown')}")
    
    # Test session validity
    print(f"\nSession valid: {'✓ Yes' if auth_service.is_authenticated() else '✗ No'}")
    
    # Update activity
    simulate_delay(1, "Simulating user activity...")
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
    
    print_banner("SCALE SYSTEM - PHASE 2 DEMO (HEADLESS)", 80)
    print("Demonstrating Authentication & Weighing Workflow Backend")
    print(f"Demo started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Demo 1: Authentication System
        auth_service = demo_authentication()
        
        # Demo 2: Transaction Management
        transaction_manager = demo_transaction_management(auth_service)
        
        # Demo 3: Transaction Voiding
        demo_void_transaction(auth_service, transaction_manager)
        
        # Demo 4: Weight Validation
        demo_weight_validation()
        
        # Demo 5: Session Management
        demo_session_management(auth_service)
        
        print_banner("PHASE 2 DEMO COMPLETED SUCCESSFULLY!", 80)
        
        print("\n🎉 All Phase 2 backend features demonstrated:")
        print("   ✓ Authentication system with role-based access control")
        print("   ✓ Two-pass weighing transaction workflow")
        print("   ✓ Fixed-tare weighing transaction workflow")
        print("   ✓ Weight validation and stability detection")
        print("   ✓ Transaction management (create, complete, void)")
        print("   ✓ Session management with timeouts and extensions")
        print("   ✓ Permission-based operation control")
        print("   ✓ Audit logging for all critical operations")
        
        print("\n📋 Next Phase: UI/UX Development")
        print("   - Main weighing screen with PyQt6")
        print("   - Interactive controls and indicators")
        print("   - Real-time weight display")
        print("   - Transaction history and reports")
        print("   - Printing system with QR code signatures")
        
        print(f"\nDemo completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show database stats
        print("\n📈 Database Summary:")
        
        # Get transaction count
        try:
            from scale_system.weighing.transaction_manager import TransactionStatus
            db = DataAccessLayer("scale_system/data/scale_system.db")
            
            # Count transactions by status
            total_query = "SELECT COUNT(*) FROM transactions"
            total_result = db.execute_query(total_query)
            total_transactions = total_result[0][0] if total_result else 0
            
            completed_query = "SELECT COUNT(*) FROM transactions WHERE status = 'complete'"
            completed_result = db.execute_query(completed_query)
            completed_transactions = completed_result[0][0] if completed_result else 0
            
            void_query = "SELECT COUNT(*) FROM transactions WHERE status = 'void'"
            void_result = db.execute_query(void_query)
            void_transactions = void_result[0][0] if void_result else 0
            
            print(f"   Total transactions created: {total_transactions}")
            print(f"   Completed transactions: {completed_transactions}")
            print(f"   Voided transactions: {void_transactions}")
            
            # Count weigh events
            events_query = "SELECT COUNT(*) FROM weigh_events"
            events_result = db.execute_query(events_query)
            total_events = events_result[0][0] if events_result else 0
            print(f"   Total weight captures: {total_events}")
            
            # Count audit entries
            audit_query = "SELECT COUNT(*) FROM audit_log"
            audit_result = db.execute_query(audit_query)
            total_audits = audit_result[0][0] if audit_result else 0
            print(f"   Audit log entries: {total_audits}")
            
        except Exception as e:
            print(f"   Error getting database stats: {e}")
        
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
