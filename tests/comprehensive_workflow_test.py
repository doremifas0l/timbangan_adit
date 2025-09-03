#!/usr/bin/env python3
"""
Comprehensive Workflow Testing System for SCALE System
Tests complete weighing workflows with simulated data
"""

import sys
import os
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Add the current directory to the path
sys.path.insert(0, os.path.abspath('.'))

class WorkflowTestResult(Enum):
    """Test result status"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

@dataclass
class TestCase:
    """Individual test case"""
    name: str
    description: str
    test_function: str
    expected_result: Any = None
    timeout: float = 30.0
    prerequisites: List[str] = None

@dataclass
class TestResult:
    """Test execution result"""
    test_case: TestCase
    result: WorkflowTestResult
    execution_time: float
    message: str
    details: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class WorkflowTester:
    """Comprehensive workflow testing system"""
    
    def __init__(self):
        self.auth_service = None
        self.workflow_controller = None
        self.data_access = None
        self.mock_serial = None
        self.test_results: List[TestResult] = []
        self.test_data = {}
        
    def initialize_system(self) -> bool:
        """Initialize all system components for testing"""
        print("\n\ud83d\udd0d Initializing System Components...")
        
        try:
            # Initialize authentication service
            from scale_system.auth.auth_service import AuthenticationService
            self.auth_service = AuthenticationService()
            print("\u2705 Authentication service initialized")
            
            # Initialize data access layer
            from scale_system.database.data_access import DataAccessLayer
            from scale_system.core.config import DATABASE_PATH
            self.data_access = DataAccessLayer(str(DATABASE_PATH))
            print("\u2705 Data access layer initialized")
            
            # Initialize workflow controller
            from scale_system.weighing.workflow_controller import WorkflowController
            self.workflow_controller = WorkflowController()
            print("\u2705 Workflow controller initialized")
            
            # Initialize mock serial service
            from scale_system.testing.mock_serial_service import MockSerialService
            from scale_system.hardware.serial_service import SerialProfile
            
            profile = SerialProfile(port="TEST_PORT", protocol="simulation")
            self.mock_serial = MockSerialService(profile)
            
            if self.mock_serial.connect():
                self.mock_serial.start_monitoring()
                print("\u2705 Mock serial service initialized")
            else:
                print("\u274c Mock serial service failed to initialize")
                return False
            
            return True
            
        except Exception as e:
            print(f"\u274c System initialization failed: {e}")
            return False
    
    def cleanup_system(self):
        """Clean up system components after testing"""
        print("\n\ud83e\uddf9 Cleaning up system components...")
        
        try:
            if self.mock_serial:
                self.mock_serial.disconnect()
                print("\u2705 Mock serial service cleaned up")
            
            if self.auth_service:
                if hasattr(self.auth_service, 'logout_current_user'):
                    self.auth_service.logout_current_user()
                print("\u2705 Authentication service cleaned up")
            
        except Exception as e:
            print(f"\u26a0\ufe0f Cleanup warning: {e}")
    
    def test_authentication_workflow(self) -> TestResult:
        """Test complete authentication workflow"""
        test_case = TestCase(
            name="Authentication Workflow",
            description="Test login, session management, and logout",
            test_function="test_authentication_workflow"
        )
        
        start_time = time.time()
        
        try:
            # Test login
            session = self.auth_service.login_user("admin", "1234")
            if not session:
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="Login failed"
                )
            
            # Verify session
            current_session = self.auth_service.get_current_session()
            if not current_session or current_session.username != "admin":
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="Session verification failed"
                )
            
            # Store session for other tests
            self.test_data['admin_session'] = current_session
            
            return TestResult(
                test_case=test_case,
                result=WorkflowTestResult.PASSED,
                execution_time=time.time() - start_time,
                message="Authentication workflow completed successfully",
                details={'session_id': session.user_id, 'role': session.role}
            )
            
        except Exception as e:
            return TestResult(
                test_case=test_case,
                result=WorkflowTestResult.ERROR,
                execution_time=time.time() - start_time,
                message=f"Authentication workflow error: {e}"
            )
    
    def test_weight_simulation(self) -> TestResult:
        """Test weight simulation functionality"""
        test_case = TestCase(
            name="Weight Simulation",
            description="Test weight simulator and mock serial communication",
            test_function="test_weight_simulation"
        )
        
        start_time = time.time()
        
        try:
            # Start vehicle simulation
            self.mock_serial.simulate_vehicle_entry(
                vehicle_type="heavy_truck",
                vehicle_id="TEST-001",
                cargo_percentage=0.8
            )
            
            # Wait for weight readings
            time.sleep(2.0)
            
            # Get readings
            readings = self.mock_serial.get_all_readings()
            if not readings:
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="No weight readings received"
                )
            
            # Verify readings are realistic
            latest_reading = readings[-1]
            if latest_reading.weight <= 0 or latest_reading.weight > 100000:
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message=f"Unrealistic weight reading: {latest_reading.weight}"
                )
            
            # Store reading for other tests
            self.test_data['last_weight_reading'] = latest_reading
            
            return TestResult(
                test_case=test_case,
                result=WorkflowTestResult.PASSED,
                execution_time=time.time() - start_time,
                message="Weight simulation working correctly",
                details={
                    'readings_count': len(readings),
                    'latest_weight': latest_reading.weight,
                    'is_stable': latest_reading.stable
                }
            )
            
        except Exception as e:
            return TestResult(
                test_case=test_case,
                result=WorkflowTestResult.ERROR,
                execution_time=time.time() - start_time,
                message=f"Weight simulation error: {e}"
            )
    
    def test_transaction_creation(self) -> TestResult:
        """Test transaction creation workflow"""
        test_case = TestCase(
            name="Transaction Creation",
            description="Test creating a new weighing transaction",
            test_function="test_transaction_creation"
        )
        
        start_time = time.time()
        
        try:
            # Ensure user is logged in
            if 'admin_session' not in self.test_data:
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="Authentication required (prerequisite failed)"
                )
            
            session = self.test_data['admin_session']
            
            # Create a transaction
            vehicle_no = "TEST-VEHICLE-001"
            transaction_id = self.data_access.create_transaction(
                vehicle_no=vehicle_no,
                mode="two_pass",
                operator_id=session.user_id,
                notes="Automated test transaction"
            )
            
            if not transaction_id:
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="Failed to create transaction"
                )
            
            # Verify transaction exists
            transaction = self.data_access.get_transaction(transaction_id)
            if not transaction:
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="Transaction not found after creation"
                )
            
            # Store transaction for other tests
            self.test_data['test_transaction'] = transaction
            self.test_data['test_transaction_id'] = transaction_id
            
            return TestResult(
                test_case=test_case,
                result=WorkflowTestResult.PASSED,
                execution_time=time.time() - start_time,
                message="Transaction created successfully",
                details={
                    'transaction_id': transaction_id,
                    'vehicle_no': vehicle_no,
                    'ticket_no': transaction.get('ticket_no'),
                    'status': transaction.get('status')
                }
            )
            
        except Exception as e:
            return TestResult(
                test_case=test_case,
                result=WorkflowTestResult.ERROR,
                execution_time=time.time() - start_time,
                message=f"Transaction creation error: {e}"
            )
    
    def test_weight_capture(self) -> TestResult:
        """Test weight capture workflow"""
        test_case = TestCase(
            name="Weight Capture",
            description="Test capturing weight readings for a transaction",
            test_function="test_weight_capture"
        )
        
        start_time = time.time()
        
        try:
            # Check prerequisites
            if 'test_transaction_id' not in self.test_data:
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="Transaction required (prerequisite failed)"
                )
            
            if 'last_weight_reading' not in self.test_data:
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="Weight reading required (prerequisite failed)"
                )
            
            transaction_id = self.test_data['test_transaction_id']
            weight_reading = self.test_data['last_weight_reading']
            
            # Wait for stable weight
            stable_reading = None
            attempts = 0
            max_attempts = 10
            
            while attempts < max_attempts:
                reading = self.mock_serial.get_latest_reading()
                if reading and reading.stable:
                    stable_reading = reading
                    break
                time.sleep(0.5)
                attempts += 1
            
            if not stable_reading:
                # Force stability for testing
                stable_reading = weight_reading
                stable_reading.stable = True
            
            # Capture the weight
            weigh_event_id = self.data_access.create_weigh_event(
                transaction_id=transaction_id,
                seq=1,  # First weighing (tare)
                gross_flag=0,  # Tare weight
                weight=stable_reading.weight,
                stable=1 if stable_reading.stable else 0,
                raw_payload=stable_reading.raw_data
            )
            
            if not weigh_event_id:
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="Failed to capture weight event"
                )
            
            # Verify weight event
            events = self.data_access.get_transaction_weigh_events(transaction_id)
            if not events or len(events) == 0:
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="Weight event not found after capture"
                )
            
            self.test_data['tare_weight_event'] = weigh_event_id
            
            return TestResult(
                test_case=test_case,
                result=WorkflowTestResult.PASSED,
                execution_time=time.time() - start_time,
                message="Weight captured successfully",
                details={
                    'event_id': weigh_event_id,
                    'weight': stable_reading.weight,
                    'stable': stable_reading.stable,
                    'events_count': len(events)
                }
            )
            
        except Exception as e:
            return TestResult(
                test_case=test_case,
                result=WorkflowTestResult.ERROR,
                execution_time=time.time() - start_time,
                message=f"Weight capture error: {e}"
            )
    
    def test_two_pass_workflow(self) -> TestResult:
        """Test complete two-pass weighing workflow"""
        test_case = TestCase(
            name="Two-Pass Workflow",
            description="Test complete two-pass weighing process",
            test_function="test_two_pass_workflow"
        )
        
        start_time = time.time()
        
        try:
            # Check prerequisites
            if 'test_transaction_id' not in self.test_data:
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="Transaction required (prerequisite failed)"
                )
            
            transaction_id = self.test_data['test_transaction_id']
            
            # Simulate gross weight capture
            self.mock_serial.simulate_vehicle_exit()  # Exit and re-enter with cargo
            time.sleep(1.0)
            
            # Simulate loaded vehicle entering
            self.mock_serial.simulate_vehicle_entry(
                vehicle_type="heavy_truck",
                vehicle_id="TEST-001",
                cargo_percentage=1.0  # Fully loaded
            )
            
            time.sleep(2.0)  # Wait for weight to stabilize
            
            # Get gross weight reading
            gross_reading = self.mock_serial.get_latest_reading()
            if not gross_reading:
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="No gross weight reading available"
                )
            
            # Capture gross weight
            gross_event_id = self.data_access.create_weigh_event(
                transaction_id=transaction_id,
                seq=2,  # Second weighing (gross)
                gross_flag=1,  # Gross weight
                weight=gross_reading.weight,
                stable=1 if gross_reading.stable else 0,
                raw_payload=gross_reading.raw_data
            )
            
            # Get tare weight from previous event
            events = self.data_access.get_transaction_weigh_events(transaction_id)
            tare_weight = 0.0
            for event in events:
                if event['gross_flag'] == 0:  # Tare weight
                    tare_weight = event['weight']
                    break
            
            # Calculate net weight
            net_weight = gross_reading.weight - tare_weight
            
            # Complete transaction
            session = self.test_data['admin_session']
            self.data_access.complete_transaction(
                transaction_id=transaction_id,
                net_weight=net_weight,
                operator_close_id=session.user_id
            )
            
            # Verify transaction completion
            completed_transaction = self.data_access.get_transaction(transaction_id)
            if completed_transaction['status'] != 'complete':
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="Transaction not marked as complete"
                )
            
            return TestResult(
                test_case=test_case,
                result=WorkflowTestResult.PASSED,
                execution_time=time.time() - start_time,
                message="Two-pass workflow completed successfully",
                details={
                    'tare_weight': tare_weight,
                    'gross_weight': gross_reading.weight,
                    'net_weight': net_weight,
                    'transaction_status': completed_transaction['status'],
                    'ticket_no': completed_transaction['ticket_no']
                }
            )
            
        except Exception as e:
            return TestResult(
                test_case=test_case,
                result=WorkflowTestResult.ERROR,
                execution_time=time.time() - start_time,
                message=f"Two-pass workflow error: {e}"
            )
    
    def test_data_persistence(self) -> TestResult:
        """Test data persistence and retrieval"""
        test_case = TestCase(
            name="Data Persistence",
            description="Test data is properly stored and retrievable",
            test_function="test_data_persistence"
        )
        
        start_time = time.time()
        
        try:
            # Test transaction retrieval
            transactions = self.data_access.get_recent_transactions(limit=5)
            if not transactions:
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="No transactions found in database"
                )
            
            # Test weigh events retrieval
            if 'test_transaction_id' in self.test_data:
                transaction_id = self.test_data['test_transaction_id']
                events = self.data_access.get_transaction_weigh_events(transaction_id)
                
                if not events:
                    return TestResult(
                        test_case=test_case,
                        result=WorkflowTestResult.FAILED,
                        execution_time=time.time() - start_time,
                        message="No weigh events found for test transaction"
                    )
            
            # Test user data
            users = self.data_access.execute_query("SELECT COUNT(*) as count FROM users")
            if not users or users[0]['count'] == 0:
                return TestResult(
                    test_case=test_case,
                    result=WorkflowTestResult.FAILED,
                    execution_time=time.time() - start_time,
                    message="No users found in database"
                )
            
            return TestResult(
                test_case=test_case,
                result=WorkflowTestResult.PASSED,
                execution_time=time.time() - start_time,
                message="Data persistence verified",
                details={
                    'transactions_count': len(transactions),
                    'users_count': users[0]['count'],
                    'events_count': len(events) if 'events' in locals() else 0
                }
            )
            
        except Exception as e:
            return TestResult(
                test_case=test_case,
                result=WorkflowTestResult.ERROR,
                execution_time=time.time() - start_time,
                message=f"Data persistence error: {e}"
            )
    
    def run_comprehensive_tests(self) -> bool:
        """Run all workflow tests"""
        print("\n" + "="*80)
        print("   COMPREHENSIVE WORKFLOW TESTING SYSTEM")
        print("="*80)
        
        if not self.initialize_system():
            print("\u274c System initialization failed - aborting tests")
            return False
        
        # Define test sequence
        test_methods = [
            self.test_authentication_workflow,
            self.test_weight_simulation,
            self.test_transaction_creation,
            self.test_weight_capture,
            self.test_two_pass_workflow,
            self.test_data_persistence
        ]
        
        print(f"\n\ud83d\udcca Running {len(test_methods)} workflow tests...\n")
        
        # Execute tests
        for test_method in test_methods:
            print(f"\u25b6\ufe0f Running {test_method.__name__.replace('test_', '').replace('_', ' ').title()}...")
            
            result = test_method()
            self.test_results.append(result)
            
            if result.result == WorkflowTestResult.PASSED:
                print(f"   \u2705 PASSED - {result.message} ({result.execution_time:.2f}s)")
                if result.details:
                    for key, value in result.details.items():
                        print(f"      {key}: {value}")
            elif result.result == WorkflowTestResult.FAILED:
                print(f"   \u274c FAILED - {result.message} ({result.execution_time:.2f}s)")
            elif result.result == WorkflowTestResult.ERROR:
                print(f"   \u2757 ERROR - {result.message} ({result.execution_time:.2f}s)")
            
            print()  # Empty line for readability
        
        # Cleanup
        self.cleanup_system()
        
        # Generate summary
        return self._generate_test_summary()
    
    def _generate_test_summary(self) -> bool:
        """Generate and display test summary"""
        print("\n" + "="*80)
        print("   WORKFLOW TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for r in self.test_results if r.result == WorkflowTestResult.PASSED)
        failed = sum(1 for r in self.test_results if r.result == WorkflowTestResult.FAILED)
        errors = sum(1 for r in self.test_results if r.result == WorkflowTestResult.ERROR)
        total = len(self.test_results)
        
        total_time = sum(r.execution_time for r in self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} \u2705")
        print(f"Failed: {failed} \u274c")
        print(f"Errors: {errors} \u2757")
        print(f"Total Execution Time: {total_time:.2f} seconds")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        print("\n" + "-"*80)
        print("DETAILED RESULTS:")
        print("-"*80)
        
        for result in self.test_results:
            status_icon = {
                WorkflowTestResult.PASSED: "\u2705",
                WorkflowTestResult.FAILED: "\u274c",
                WorkflowTestResult.ERROR: "\u2757"
            }.get(result.result, "\u2753")
            
            print(f"{status_icon} {result.test_case.name:<30} {result.result.value.upper():<8} {result.execution_time:.2f}s")
            print(f"   {result.message}")
            
            if result.details:
                for key, value in result.details.items():
                    print(f"   • {key}: {value}")
            print()
        
        success = passed == total
        
        if success:
            print("\n\ud83c\udf89 ALL WORKFLOW TESTS PASSED! System is fully functional! \ud83c\udf89")
        else:
            print(f"\n\u26a0\ufe0f  {failed + errors} tests failed. System issues need to be addressed.")
        
        return success
    
    def export_test_results(self, filename: str = None) -> str:
        """Export test results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"workflow_test_results_{timestamp}.json"
        
        # Convert results to serializable format
        serializable_results = []
        for result in self.test_results:
            serializable_results.append({
                'test_name': result.test_case.name,
                'description': result.test_case.description,
                'result': result.result.value,
                'execution_time': result.execution_time,
                'message': result.message,
                'details': result.details,
                'timestamp': result.timestamp.isoformat()
            })
        
        # Create summary
        export_data = {
            'test_run_info': {
                'timestamp': datetime.now().isoformat(),
                'total_tests': len(self.test_results),
                'passed': sum(1 for r in self.test_results if r.result == WorkflowTestResult.PASSED),
                'failed': sum(1 for r in self.test_results if r.result == WorkflowTestResult.FAILED),
                'errors': sum(1 for r in self.test_results if r.result == WorkflowTestResult.ERROR)
            },
            'test_results': serializable_results,
            'test_data': self.test_data
        }
        
        # Write to file
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"\u2705 Test results exported to: {filename}")
        return filename

def main():
    """Main test execution function"""
    tester = WorkflowTester()
    
    try:
        success = tester.run_comprehensive_tests()
        
        # Export results
        export_file = tester.export_test_results()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\u26a0\ufe0f Test execution interrupted by user")
        tester.cleanup_system()
        return 2
    except Exception as e:
        print(f"\n\u274c Test execution failed: {e}")
        tester.cleanup_system()
        return 3

if __name__ == "__main__":
    sys.exit(main())
