#!/usr/bin/env python3
"""
Simple Headless Authentication Test
Basic authentication testing without Unicode characters
"""

import sys
import os
from datetime import datetime

# Add the current directory to the path
sys.path.insert(0, os.path.abspath('.'))

def test_basic_authentication():
    """Test basic authentication functionality"""
    print("\n" + "="*60)
    print("BASIC AUTHENTICATION TEST")
    print("="*60)
    
    try:
        # Initialize auth service
        from scale_system.auth.auth_service import AuthenticationService
        auth_service = AuthenticationService()
        print("[+] Authentication service initialized")
        
        # Test credentials
        test_cases = [
            ("admin", "1234", True, "Admin"),
            ("supervisor", "2345", True, "Supervisor"),
            ("operator", "3456", True, "Operator"),
            ("admin", "wrong", False, None),
            ("invalid", "1234", False, None)
        ]
        
        passed = 0
        total = len(test_cases)
        
        print("\nTesting credentials:")
        for username, pin, should_pass, expected_role in test_cases:
            try:
                result = auth_service.authenticate_user(username, pin)
                
                if should_pass:
                    if result and result.get('role') == expected_role:
                        print(f"[+] {username}/{pin}: PASS - Role: {result['role']}")
                        passed += 1
                    else:
                        print(f"[-] {username}/{pin}: FAIL - Expected {expected_role}, got {result}")
                else:
                    if result is None:
                        print(f"[+] {username}/{pin}: PASS - Correctly rejected")
                        passed += 1
                    else:
                        print(f"[-] {username}/{pin}: FAIL - Should have been rejected")
                        
            except Exception as e:
                print(f"[-] {username}/{pin}: ERROR - {e}")
        
        print(f"\nCredential Test Results: {passed}/{total} passed")
        
        # Test session management
        print("\nTesting session management:")
        session = auth_service.login_user("admin", "1234")
        if session:
            print(f"[+] Login successful: {session.username} ({session.role})")
            
            # Check current session
            current = auth_service.get_current_session()
            if current and current.username == "admin":
                print(f"[+] Current session verified: {current.username}")
                passed += 1
            else:
                print(f"[-] Current session verification failed")
            
            # Check login status
            if auth_service.is_user_logged_in():
                print(f"[+] User logged in status: True")
                passed += 1
            else:
                print(f"[-] User logged in status: False (unexpected)")
            
            # Logout
            auth_service.logout_current_user()
            if not auth_service.is_user_logged_in():
                print(f"[+] Logout successful")
                passed += 1
            else:
                print(f"[-] Logout failed")
                
        else:
            print(f"[-] Login failed")
        
        total += 3  # Added 3 session tests
        
        print(f"\nFinal Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("\n[SUCCESS] All authentication tests passed!")
            return True
        else:
            print(f"\n[WARNING] {total-passed} tests failed")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Authentication test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_weight_simulation():
    """Test weight simulation system"""
    print("\n" + "="*60)
    print("WEIGHT SIMULATION TEST")
    print("="*60)
    
    try:
        from scale_system.testing.weight_simulator import get_weight_simulator
        from scale_system.testing.mock_serial_service import MockSerialService
        from scale_system.hardware.serial_service import SerialProfile
        
        # Test weight simulator
        simulator = get_weight_simulator()
        print("[+] Weight simulator initialized")
        
        # Start simulation
        vehicle = simulator.start_simulation()
        print(f"[+] Vehicle simulation started: {vehicle['id']}")
        print(f"    Vehicle weight: {vehicle['total_weight']:.1f} kg")
        
        # Get weight readings
        readings = []
        for i in range(5):
            reading = simulator.get_weight_reading()
            readings.append(reading)
            stable = "STABLE" if reading.is_stable else "UNSTABLE"
            print(f"    Reading {i+1}: {reading.gross_weight:.1f} kg ({stable})")
        
        # Test mock serial service
        profile = SerialProfile(port="TEST_PORT", protocol="simulation")
        mock_serial = MockSerialService(profile)
        
        if mock_serial.connect():
            print("[+] Mock serial service connected")
            
            mock_serial.start_monitoring()
            print("[+] Mock serial monitoring started")
            
            import time
            time.sleep(1.0)  # Let it collect some data
            
            serial_readings = mock_serial.get_all_readings()
            print(f"[+] Collected {len(serial_readings)} serial readings")
            
            mock_serial.disconnect()
            print("[+] Mock serial service disconnected")
            
            simulator.stop_simulation()
            print("[+] Weight simulation stopped")
            
            return len(readings) > 0 and len(serial_readings) > 0
        else:
            print("[-] Mock serial service connection failed")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Weight simulation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test runner"""
    print("SCALE SYSTEM - HEADLESS TESTING")
    print("=" * 80)
    print(f"Started at: {datetime.now()}")
    print("=" * 80)
    
    test_results = []
    
    # Run authentication test
    print("\n[1/2] Running authentication test...")
    auth_result = test_basic_authentication()
    test_results.append(("Authentication", auth_result))
    
    # Run weight simulation test
    print("\n[2/2] Running weight simulation test...")
    sim_result = test_weight_simulation()
    test_results.append(("Weight Simulation", sim_result))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:<30} {status}")
    
    print(f"\nOverall: {passed}/{total} test suites passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n[SUCCESS] All test suites passed! System is ready for use.")
        return 0
    else:
        print(f"\n[WARNING] {total-passed} test suites failed. Issues need attention.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
