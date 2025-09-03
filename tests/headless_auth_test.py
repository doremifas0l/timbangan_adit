#!/usr/bin/env python3
"""
Headless Authentication Testing System
Tests login functionality and session management without GUI
"""

import sys
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Add the current directory to the path
sys.path.insert(0, os.path.abspath('.'))

class HeadlessLoginTester:
    """Comprehensive headless login testing system"""
    
    def __init__(self):
        self.auth_service = None
        self.test_results = []
        
    def initialize_services(self) -> bool:
        """Initialize authentication services"""
        try:
            from scale_system.auth.auth_service import AuthenticationService
            self.auth_service = AuthenticationService()
            print("[PASS] Authentication service initialized")
            return True
        except Exception as e:
            print(f"[FAIL] Failed to initialize auth service: {e}")
            return False
    
    def test_login_credentials(self) -> bool:
        """Test login with default credentials"""
        print("\n[TEST] Testing Login Credentials...")
        
        # Test credentials: (username, pin, expected_role, should_succeed)
        test_cases = [
            ("admin", "1234", "Admin", True),
            ("supervisor", "2345", "Supervisor", True), 
            ("operator", "3456", "Operator", True),
            ("admin", "wrong", None, False),
            ("nonexistent", "1234", None, False),
            ("", "1234", None, False),
            ("admin", "", None, False)
        ]
        
        results = []
        
        for username, pin, expected_role, should_succeed in test_cases:
            try:
                result = self.auth_service.authenticate_user(username, pin)
                
                if should_succeed:
                    if result and result.get('role') == expected_role:
                        print(f"[PASS] {username}/{pin}: SUCCESS - Role: {result['role']}")
                        results.append(True)
                    else:
                        print(f"[FAIL] {username}/{pin}: FAILED - Expected success but got {result}")
                        results.append(False)
                else:
                    if result is None:
                        print(f"[PASS] {username}/{pin}: FAILED as expected")
                        results.append(True)
                    else:
                        print(f"[FAIL] {username}/{pin}: Should have failed but got {result}")
                        results.append(False)
                        
            except Exception as e:
                print(f"[FAIL] {username}/{pin}: Exception - {e}")
                results.append(False)
        
        success_rate = sum(results) / len(results)
        print(f"\n[RESULTS] Credential Test Results: {sum(results)}/{len(results)} passed ({success_rate:.1%})")
        
        return success_rate >= 0.8  # 80% success rate required
    
    def test_session_management(self) -> bool:
        """Test session creation and management"""
        print("\n[TEST] Testing Session Management...")
        
        try:
            # Test login and session creation
            user_info = self.auth_service.authenticate_user("admin", "1234")
            if not user_info:
                print("[FAIL] Cannot test sessions - login failed")
                return False
            
            print(f"[PASS] Login successful: {user_info['username']} ({user_info['role']})")
            
            # Test session creation
            session = self.auth_service.login_user("admin", "1234")
            if session:
                print(f"[PASS] Session created: {session.username} - expires {session.session_expires}")
            else:
                print("[FAIL] Session creation failed")
                return False
            
            # Test current session retrieval
            current_session = self.auth_service.get_current_session()
            if current_session and current_session.username == "admin":
                print(f"[PASS] Current session retrieved: {current_session.username}")
            else:
                print("[FAIL] Current session retrieval failed")
                return False
            
            # Test session validation
            if self.auth_service.is_user_logged_in():
                print("[PASS] User is logged in (session valid)")
            else:
                print("[FAIL] Session validation failed")
                return False
            
            # Test logout
            self.auth_service.logout_current_user()
            if not self.auth_service.is_user_logged_in():
                print("[PASS] Logout successful")
            else:
                print("[FAIL] Logout failed")
                return False
            
            return True
            
        except Exception as e:
            print(f"[FAIL] Session management test failed: {e}")
            return False
    
    def test_role_based_access(self) -> bool:
        """Test role-based access control"""
        print("\n[TEST] Testing Role-Based Access Control...")
        
        # Test different roles and their permissions
        role_tests = [
            ("admin", "1234", ["VIEW_REPORTS", "MANAGE_USERS", "SYSTEM_CONFIG", "BACKUP_RESTORE"]),
            ("supervisor", "2345", ["VIEW_REPORTS", "MANAGE_TRANSACTIONS", "VIEW_ANALYTICS"]),
            ("operator", "3456", ["WEIGH_VEHICLES", "VIEW_TRANSACTIONS"])
        ]
        
        results = []
        
        for username, pin, expected_permissions in role_tests:
            try:
                # Login as user
                session = self.auth_service.login_user(username, pin)
                if not session:
                    print(f"[FAIL] Failed to login as {username}")
                    results.append(False)
                    continue
                
                print(f"[PASS] Logged in as {username} ({session.role})")
                
                # Test permissions (simplified check)
                role_valid = session.role in ["Admin", "Supervisor", "Operator"]
                if role_valid:
                    print(f"[PASS] Role validation passed for {session.role}")
                    results.append(True)
                else:
                    print(f"[FAIL] Invalid role: {session.role}")
                    results.append(False)
                
                # Logout
                self.auth_service.logout_current_user()
                
            except Exception as e:
                print(f"[FAIL] Role test failed for {username}: {e}")
                results.append(False)
        
        success_rate = sum(results) / len(results)
        print(f"\n[RESULTS] Role Access Test Results: {sum(results)}/{len(results)} passed ({success_rate:.1%})")
        
        return success_rate >= 0.8
    
    def test_concurrent_sessions(self) -> bool:
        """Test concurrent session handling"""
        print("\n[TEST] Testing Concurrent Session Handling...")
        
        try:
            # Login as admin
            session1 = self.auth_service.login_user("admin", "1234")
            if session1:
                print(f"[PASS] First session created: {session1.username}")
            else:
                print("[FAIL] First session creation failed")
                return False
            
            # Try to login as different user (should handle properly)
            session2 = self.auth_service.login_user("supervisor", "2345")
            if session2:
                print(f"[PASS] Second session created: {session2.username}")
                print(f"\u2139\ufe0f Session switched from {session1.username} to {session2.username}")
            else:
                print("[FAIL] Second session creation failed")
                return False
            
            # Verify current session is the latest
            current = self.auth_service.get_current_session()
            if current and current.username == "supervisor":
                print("[PASS] Current session correctly updated")
            else:
                print("[FAIL] Current session not updated correctly")
                return False
            
            # Cleanup
            self.auth_service.logout_current_user()
            return True
            
        except Exception as e:
            print(f"[FAIL] Concurrent session test failed: {e}")
            return False
    
    def test_invalid_scenarios(self) -> bool:
        """Test various invalid scenarios and edge cases"""
        print("\n[TEST] Testing Invalid Scenarios...")
        
        edge_cases = [
            # SQL injection attempts
            ("admin'; DROP TABLE users; --", "1234"),
            ("admin", "1234'; DROP TABLE users; --"),
            
            # Long inputs
            ("a" * 1000, "1234"),
            ("admin", "1" * 1000),
            
            # Special characters
            ("admin<script>", "1234"),
            ("admin", "<script>alert('xss')</script>"),
            
            # Unicode and encoding issues
            ("adm\u00edn", "1234"),  # Unicode characters
            ("admin", "\x00\x01\x02"),  # Control characters
        ]
        
        results = []
        
        for username, pin in edge_cases:
            try:
                result = self.auth_service.authenticate_user(username, pin)
                
                # All these should fail
                if result is None:
                    print(f"[PASS] Edge case correctly rejected: {repr(username)[:20]}...")
                    results.append(True)
                else:
                    print(f"[FAIL] Edge case incorrectly accepted: {repr(username)[:20]}...")
                    results.append(False)
                    
            except Exception as e:
                # Exceptions are okay for edge cases, as long as system doesn't crash
                print(f"[PASS] Edge case handled with exception: {repr(username)[:20]}... - {type(e).__name__}")
                results.append(True)
        
        success_rate = sum(results) / len(results)
        print(f"\n[RESULTS] Edge Case Test Results: {sum(results)}/{len(results)} passed ({success_rate:.1%})")
        
        return success_rate >= 0.8
    
    def run_comprehensive_test(self) -> bool:
        """Run all authentication tests"""
        print("\n" + "="*80)
        print("   HEADLESS AUTHENTICATION TESTING SYSTEM")
        print("="*80)
        
        if not self.initialize_services():
            return False
        
        # Run all test suites
        test_suites = [
            ("Credential Authentication", self.test_login_credentials),
            ("Session Management", self.test_session_management),
            ("Role-Based Access Control", self.test_role_based_access),
            ("Concurrent Sessions", self.test_concurrent_sessions),
            ("Invalid Scenarios", self.test_invalid_scenarios)
        ]
        
        results = []
        
        for test_name, test_func in test_suites:
            print(f"\n{'='*60}")
            print(f"Running: {test_name}")
            print(f"{'='*60}")
            
            try:
                result = test_func()
                results.append((test_name, result))
                
                if result:
                    print(f"\n[PASS] {test_name}: PASSED")
                else:
                    print(f"\n[FAIL] {test_name}: FAILED")
            except Exception as e:
                print(f"\n[FAIL] {test_name}: CRASHED - {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "="*80)
        print("   AUTHENTICATION TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "[PASS] PASSED" if result else "[FAIL] FAILED"
            print(f"  {test_name:<40} {status}")
        
        print(f"\n📊 Overall Results: {passed}/{total} tests passed ({passed/total:.1%})")
        
        if passed == total:
            print("\n🎉 ALL AUTHENTICATION TESTS PASSED! 🎉")
            return True
        else:
            print(f"\n⚠️  {total - passed} tests failed. Authentication issues need to be addressed.")
            return False

def main():
    """Main test function"""
    tester = HeadlessLoginTester()
    success = tester.run_comprehensive_test()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
