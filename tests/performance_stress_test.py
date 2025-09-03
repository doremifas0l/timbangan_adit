#!/usr/bin/env python3
"""
Performance and Stress Testing Suite for SCALE System v2.0
Tests system performance, scalability, and reliability under load
"""

import sys
import os
import time
import threading
import concurrent.futures
import uuid
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, os.path.abspath('.'))

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    operation_name: str
    total_operations: int
    successful_operations: int
    failed_operations: int
    total_time: float
    min_time: float
    max_time: float
    avg_time: float
    operations_per_second: float
    
    @property
    def success_rate(self) -> float:
        return (self.successful_operations / self.total_operations) * 100 if self.total_operations > 0 else 0

class PerformanceTestSuite:
    """Performance and stress testing system"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.auth_service = None
        self.data_access = None
        self.mock_serial = None
        self.performance_results: List[PerformanceMetrics] = []
        self.stress_test_data = []
        
    def initialize_system(self) -> bool:
        """Initialize system components for performance testing"""
        try:
            from auth.auth_service import AuthenticationService
            from database.data_access import DataAccessLayer
            from core.config import DATABASE_PATH
            from testing.mock_serial_service import MockSerialService
            from hardware.serial_service import SerialProfile
            
            self.auth_service = AuthenticationService()
            self.data_access = DataAccessLayer(str(DATABASE_PATH))
            
            # Initialize mock serial for weight simulation
            profile = SerialProfile(port="PERF_TEST_PORT", protocol="simulation")
            self.mock_serial = MockSerialService(profile)
            
            return True
        except Exception as e:
            print(f"Performance test initialization error: {e}")
            return False
    
    def run_performance_test_suite(self) -> bool:
        """Execute the complete performance test suite"""
        print("\n" + "=" * 80)
        print("   SCALE SYSTEM v2.0 - PERFORMANCE & STRESS TEST SUITE")
        print("=" * 80)
        print(f"🚀 Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔥 Testing Environment: {os.getcwd()}")
        
        if not self.initialize_system():
            print("💥 CRITICAL: Performance test initialization failed")
            return False
        
        # Performance test categories
        test_categories = [
            ("💾 Database Performance", self.test_database_performance),
            ("🔐 Authentication Performance", self.test_authentication_performance),
            ("⚖️ Weight Simulation Performance", self.test_weight_simulation_performance),
            ("🔄 Transaction Processing Performance", self.test_transaction_performance),
            ("📊 Concurrent Operations", self.test_concurrent_operations),
            ("📊 Load Testing", self.test_system_under_load),
            ("🕰️ Stress Testing", self.test_system_stress),
            ("📈 Memory and Resource Usage", self.test_resource_usage)
        ]
        
        # Execute performance tests
        for category_name, test_function in test_categories:
            print(f"\n{'=' * 60}")
            print(f"{category_name}")
            print(f"{'=' * 60}")
            
            try:
                test_function()
            except Exception as e:
                print(f"❌ {category_name} failed: {e}")
        
        # Generate performance report
        return self.generate_performance_report()
    
    def test_database_performance(self):
        """Test database operation performance"""
        
        print("💾 Testing database operation performance...")
        
        # Test 1: Insert Performance
        print("\n[1/4] Insert Performance Test...")
        insert_times = []
        successful_inserts = 0
        failed_inserts = 0
        
        for i in range(100):  # 100 insert operations
            start_time = time.time()
            try:
                with self.data_access.get_connection() as conn:
                    product_id = str(uuid.uuid4())
                    conn.execute("""
                        INSERT INTO products (id, code, name, description, unit, is_active, created_at_utc)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (product_id, f'PERF_{i:04d}', f'Performance Test Product {i}', 'Test product for performance testing', 'KG', 1, datetime.utcnow().isoformat()))
                    
                successful_inserts += 1
            except Exception:
                failed_inserts += 1
            
            execution_time = time.time() - start_time
            insert_times.append(execution_time)
        
        # Calculate metrics
        total_time = sum(insert_times)
        avg_time = total_time / len(insert_times) if insert_times else 0
        min_time = min(insert_times) if insert_times else 0
        max_time = max(insert_times) if insert_times else 0
        ops_per_sec = len(insert_times) / total_time if total_time > 0 else 0
        
        insert_metrics = PerformanceMetrics(
            operation_name="Database Inserts",
            total_operations=100,
            successful_operations=successful_inserts,
            failed_operations=failed_inserts,
            total_time=total_time,
            min_time=min_time,
            max_time=max_time,
            avg_time=avg_time,
            operations_per_second=ops_per_sec
        )
        
        self.performance_results.append(insert_metrics)
        print(f"   Insert Performance: {ops_per_sec:.1f} ops/sec (avg: {avg_time*1000:.1f}ms)")
        
        # Test 2: Select Performance
        print("\n[2/4] Select Performance Test...")
        select_times = []
        successful_selects = 0
        failed_selects = 0
        
        for i in range(500):  # 500 select operations
            start_time = time.time()
            try:
                with self.data_access.get_connection() as conn:
                    conn.execute("""
                        SELECT * FROM products 
                        WHERE is_active = 1 
                        ORDER BY created_at_utc DESC 
                        LIMIT 10
                    """).fetchall()
                    
                successful_selects += 1
            except Exception:
                failed_selects += 1
            
            execution_time = time.time() - start_time
            select_times.append(execution_time)
        
        # Calculate select metrics
        total_time = sum(select_times)
        avg_time = total_time / len(select_times) if select_times else 0
        min_time = min(select_times) if select_times else 0
        max_time = max(select_times) if select_times else 0
        ops_per_sec = len(select_times) / total_time if total_time > 0 else 0
        
        select_metrics = PerformanceMetrics(
            operation_name="Database Selects",
            total_operations=500,
            successful_operations=successful_selects,
            failed_operations=failed_selects,
            total_time=total_time,
            min_time=min_time,
            max_time=max_time,
            avg_time=avg_time,
            operations_per_second=ops_per_sec
        )
        
        self.performance_results.append(select_metrics)
        print(f"   Select Performance: {ops_per_sec:.1f} ops/sec (avg: {avg_time*1000:.1f}ms)")
        
        # Test 3: Update Performance
        print("\n[3/4] Update Performance Test...")
        update_times = []
        successful_updates = 0
        failed_updates = 0
        
        # Get some test products to update
        with self.data_access.get_connection() as conn:
            test_products = conn.execute("""
                SELECT id FROM products 
                WHERE code LIKE 'PERF_%' 
                LIMIT 50
            """).fetchall()
        
        for product in test_products:
            start_time = time.time()
            try:
                with self.data_access.get_connection() as conn:
                    conn.execute("""
                        UPDATE products 
                        SET description = ? 
                        WHERE id = ?
                    """, (f'Updated at {datetime.now().isoformat()}', product['id']))
                    
                successful_updates += 1
            except Exception:
                failed_updates += 1
            
            execution_time = time.time() - start_time
            update_times.append(execution_time)
        
        # Calculate update metrics
        if update_times:
            total_time = sum(update_times)
            avg_time = total_time / len(update_times)
            min_time = min(update_times)
            max_time = max(update_times)
            ops_per_sec = len(update_times) / total_time if total_time > 0 else 0
            
            update_metrics = PerformanceMetrics(
                operation_name="Database Updates",
                total_operations=len(test_products),
                successful_operations=successful_updates,
                failed_operations=failed_updates,
                total_time=total_time,
                min_time=min_time,
                max_time=max_time,
                avg_time=avg_time,
                operations_per_second=ops_per_sec
            )
            
            self.performance_results.append(update_metrics)
            print(f"   Update Performance: {ops_per_sec:.1f} ops/sec (avg: {avg_time*1000:.1f}ms)")
        
        # Test 4: Cleanup (Delete Performance)
        print("\n[4/4] Cleanup Performance Test...")
        delete_start = time.time()
        with self.data_access.get_connection() as conn:
            result = conn.execute("DELETE FROM products WHERE code LIKE 'PERF_%'")
            deleted_count = result.rowcount
        delete_time = time.time() - delete_start
        
        print(f"   Cleanup: Deleted {deleted_count} test records in {delete_time:.2f}s")
    
    def test_authentication_performance(self):
        """Test authentication system performance"""
        
        print("🔐 Testing authentication performance...")
        
        # Test 1: Login Performance
        print("\n[1/3] Login Performance Test...")
        login_times = []
        successful_logins = 0
        failed_logins = 0
        
        for i in range(100):  # 100 login attempts
            start_time = time.time()
            try:
                session = self.auth_service.login_user("admin", "1234")
                if session:
                    successful_logins += 1
                    # Logout immediately
                    self.auth_service.logout_current_user()
                else:
                    failed_logins += 1
            except Exception:
                failed_logins += 1
            
            execution_time = time.time() - start_time
            login_times.append(execution_time)
        
        # Calculate login metrics
        total_time = sum(login_times)
        avg_time = total_time / len(login_times) if login_times else 0
        min_time = min(login_times) if login_times else 0
        max_time = max(login_times) if login_times else 0
        ops_per_sec = len(login_times) / total_time if total_time > 0 else 0
        
        login_metrics = PerformanceMetrics(
            operation_name="Authentication Logins",
            total_operations=100,
            successful_operations=successful_logins,
            failed_operations=failed_logins,
            total_time=total_time,
            min_time=min_time,
            max_time=max_time,
            avg_time=avg_time,
            operations_per_second=ops_per_sec
        )
        
        self.performance_results.append(login_metrics)
        print(f"   Login Performance: {ops_per_sec:.1f} logins/sec (avg: {avg_time*1000:.1f}ms)")
        
        # Test 2: Session Validation Performance
        print("\n[2/3] Session Validation Performance Test...")
        
        # Login once and test session validation
        session = self.auth_service.login_user("admin", "1234")
        
        if session:
            validation_times = []
            successful_validations = 0
            failed_validations = 0
            
            for i in range(1000):  # 1000 validation checks
                start_time = time.time()
                try:
                    is_logged_in = self.auth_service.is_user_logged_in()
                    if is_logged_in:
                        successful_validations += 1
                    else:
                        failed_validations += 1
                except Exception:
                    failed_validations += 1
                
                execution_time = time.time() - start_time
                validation_times.append(execution_time)
            
            # Calculate validation metrics
            total_time = sum(validation_times)
            avg_time = total_time / len(validation_times) if validation_times else 0
            min_time = min(validation_times) if validation_times else 0
            max_time = max(validation_times) if validation_times else 0
            ops_per_sec = len(validation_times) / total_time if total_time > 0 else 0
            
            validation_metrics = PerformanceMetrics(
                operation_name="Session Validations",
                total_operations=1000,
                successful_operations=successful_validations,
                failed_operations=failed_validations,
                total_time=total_time,
                min_time=min_time,
                max_time=max_time,
                avg_time=avg_time,
                operations_per_second=ops_per_sec
            )
            
            self.performance_results.append(validation_metrics)
            print(f"   Session Validation: {ops_per_sec:.1f} validations/sec (avg: {avg_time*1000:.3f}ms)")
            
            # Logout
            self.auth_service.logout_current_user()
        
        # Test 3: Failed Authentication Performance
        print("\n[3/3] Failed Authentication Performance Test...")
        failed_auth_times = []
        
        for i in range(50):  # 50 failed attempts
            start_time = time.time()
            try:
                self.auth_service.authenticate_user("invalid_user", "wrong_pin")
            except Exception:
                pass
            
            execution_time = time.time() - start_time
            failed_auth_times.append(execution_time)
        
        if failed_auth_times:
            total_time = sum(failed_auth_times)
            avg_time = total_time / len(failed_auth_times)
            ops_per_sec = len(failed_auth_times) / total_time if total_time > 0 else 0
            
            print(f"   Failed Auth: {ops_per_sec:.1f} attempts/sec (avg: {avg_time*1000:.1f}ms)")
    
    def test_weight_simulation_performance(self):
        """Test weight simulation system performance"""
        
        print("⚖️ Testing weight simulation performance...")
        
        # Initialize mock serial
        if self.mock_serial.connect():
            self.mock_serial.start_monitoring()
            time.sleep(1.0)  # Let it initialize
            
            # Test 1: Weight Reading Performance
            print("\n[1/3] Weight Reading Performance Test...")
            
            # Start vehicle simulation
            self.mock_serial.simulate_vehicle_entry(
                vehicle_type="heavy_truck",
                vehicle_id="PERF-TEST-001",
                cargo_percentage=0.75
            )
            
            reading_times = []
            successful_readings = 0
            failed_readings = 0
            
            for i in range(1000):  # 1000 weight readings
                start_time = time.time()
                try:
                    reading = self.mock_serial.get_latest_reading()
                    if reading:
                        successful_readings += 1
                    else:
                        failed_readings += 1
                except Exception:
                    failed_readings += 1
                
                execution_time = time.time() - start_time
                reading_times.append(execution_time)
                
                time.sleep(0.001)  # Small delay between readings
            
            # Calculate reading metrics
            total_time = sum(reading_times)
            avg_time = total_time / len(reading_times) if reading_times else 0
            min_time = min(reading_times) if reading_times else 0
            max_time = max(reading_times) if reading_times else 0
            ops_per_sec = len(reading_times) / total_time if total_time > 0 else 0
            
            reading_metrics = PerformanceMetrics(
                operation_name="Weight Readings",
                total_operations=1000,
                successful_operations=successful_readings,
                failed_operations=failed_readings,
                total_time=total_time,
                min_time=min_time,
                max_time=max_time,
                avg_time=avg_time,
                operations_per_second=ops_per_sec
            )
            
            self.performance_results.append(reading_metrics)
            print(f"   Reading Performance: {ops_per_sec:.1f} readings/sec (avg: {avg_time*1000:.3f}ms)")
            
            # Test 2: Vehicle Simulation Performance
            print("\n[2/3] Vehicle Simulation Performance Test...")
            simulation_times = []
            successful_simulations = 0
            failed_simulations = 0
            
            for i in range(50):  # 50 vehicle simulations
                start_time = time.time()
                try:
                    self.mock_serial.simulate_vehicle_entry(
                        vehicle_type="light_truck",
                        vehicle_id=f"PERF-{i:03d}",
                        cargo_percentage=0.5 + (i % 5) * 0.1
                    )
                    time.sleep(0.1)  # Wait for simulation to start
                    successful_simulations += 1
                except Exception:
                    failed_simulations += 1
                
                execution_time = time.time() - start_time
                simulation_times.append(execution_time)
            
            if simulation_times:
                total_time = sum(simulation_times)
                avg_time = total_time / len(simulation_times)
                min_time = min(simulation_times)
                max_time = max(simulation_times)
                ops_per_sec = len(simulation_times) / total_time if total_time > 0 else 0
                
                simulation_metrics = PerformanceMetrics(
                    operation_name="Vehicle Simulations",
                    total_operations=50,
                    successful_operations=successful_simulations,
                    failed_operations=failed_simulations,
                    total_time=total_time,
                    min_time=min_time,
                    max_time=max_time,
                    avg_time=avg_time,
                    operations_per_second=ops_per_sec
                )
                
                self.performance_results.append(simulation_metrics)
                print(f"   Simulation Performance: {ops_per_sec:.1f} simulations/sec")
            
            # Test 3: Data Collection Performance
            print("\n[3/3] Data Collection Performance Test...")
            
            time.sleep(2.0)  # Let readings accumulate
            
            collection_times = []
            for i in range(100):  # 100 data collection operations
                start_time = time.time()
                try:
                    readings = self.mock_serial.get_all_readings()
                    if readings:
                        # Process readings (simulate real workload)
                        processed = [r for r in readings if r.stable]
                except Exception:
                    pass
                
                execution_time = time.time() - start_time
                collection_times.append(execution_time)
            
            if collection_times:
                total_time = sum(collection_times)
                avg_time = total_time / len(collection_times)
                ops_per_sec = len(collection_times) / total_time if total_time > 0 else 0
                
                print(f"   Data Collection: {ops_per_sec:.1f} collections/sec (avg: {avg_time*1000:.1f}ms)")
            
            # Cleanup
            self.mock_serial.disconnect()
        else:
            print("   ⚠️ Mock serial connection failed - skipping weight simulation tests")
    
    def test_transaction_performance(self):
        """Test transaction processing performance"""
        
        print("🔄 Testing transaction processing performance...")
        
        # Ensure user is logged in
        session = self.auth_service.login_user("admin", "1234")
        if not session:
            print("   ⚠️ Authentication failed - skipping transaction tests")
            return
        
        # Test 1: Transaction Creation Performance
        print("\n[1/3] Transaction Creation Performance Test...")
        creation_times = []
        successful_creates = 0
        failed_creates = 0
        transaction_ids = []
        
        for i in range(200):  # 200 transaction creations
            start_time = time.time()
            try:
                vehicle_no = f"PERF-TRANS-{i:04d}"
                transaction_id = self.data_access.create_transaction(
                    vehicle_no=vehicle_no,
                    mode="two_pass",
                    operator_id=session.user_id,
                    notes=f"Performance test transaction {i}"
                )
                
                if transaction_id:
                    successful_creates += 1
                    transaction_ids.append(transaction_id)
                else:
                    failed_creates += 1
            except Exception:
                failed_creates += 1
            
            execution_time = time.time() - start_time
            creation_times.append(execution_time)
        
        # Calculate creation metrics
        total_time = sum(creation_times)
        avg_time = total_time / len(creation_times) if creation_times else 0
        min_time = min(creation_times) if creation_times else 0
        max_time = max(creation_times) if creation_times else 0
        ops_per_sec = len(creation_times) / total_time if total_time > 0 else 0
        
        creation_metrics = PerformanceMetrics(
            operation_name="Transaction Creation",
            total_operations=200,
            successful_operations=successful_creates,
            failed_operations=failed_creates,
            total_time=total_time,
            min_time=min_time,
            max_time=max_time,
            avg_time=avg_time,
            operations_per_second=ops_per_sec
        )
        
        self.performance_results.append(creation_metrics)
        print(f"   Creation Performance: {ops_per_sec:.1f} transactions/sec (avg: {avg_time*1000:.1f}ms)")
        
        # Test 2: Weight Event Recording Performance
        print("\n[2/3] Weight Event Recording Performance Test...")
        event_times = []
        successful_events = 0
        failed_events = 0
        
        # Use subset of transactions for weight events
        test_transactions = transaction_ids[:100]  # First 100 transactions
        
        for i, transaction_id in enumerate(test_transactions):
            start_time = time.time()
            try:
                weigh_event_id = self.data_access.create_weigh_event(
                    transaction_id=transaction_id,
                    seq=1,
                    gross_flag=0,  # Tare weight
                    weight=1500.0 + (i * 10),  # Varying weights
                    stable=1,
                    raw_payload=f"PERF_TEST_WEIGHT_{i}"
                )
                
                if weigh_event_id:
                    successful_events += 1
                else:
                    failed_events += 1
            except Exception:
                failed_events += 1
            
            execution_time = time.time() - start_time
            event_times.append(execution_time)
        
        # Calculate event metrics
        if event_times:
            total_time = sum(event_times)
            avg_time = total_time / len(event_times)
            min_time = min(event_times)
            max_time = max(event_times)
            ops_per_sec = len(event_times) / total_time if total_time > 0 else 0
            
            event_metrics = PerformanceMetrics(
                operation_name="Weight Event Recording",
                total_operations=len(test_transactions),
                successful_operations=successful_events,
                failed_operations=failed_events,
                total_time=total_time,
                min_time=min_time,
                max_time=max_time,
                avg_time=avg_time,
                operations_per_second=ops_per_sec
            )
            
            self.performance_results.append(event_metrics)
            print(f"   Event Recording: {ops_per_sec:.1f} events/sec (avg: {avg_time*1000:.1f}ms)")
        
        # Test 3: Transaction Query Performance
        print("\n[3/3] Transaction Query Performance Test...")
        query_times = []
        successful_queries = 0
        failed_queries = 0
        
        for i in range(500):  # 500 query operations
            start_time = time.time()
            try:
                with self.data_access.get_connection() as conn:
                    transactions = conn.execute("""
                        SELECT * FROM transactions 
                        WHERE created_at_utc >= datetime('now', '-1 day') 
                        ORDER BY created_at_utc DESC 
                        LIMIT 10
                    """).fetchall()
                    
                    if transactions is not None:
                        successful_queries += 1
                    else:
                        failed_queries += 1
            except Exception:
                failed_queries += 1
            
            execution_time = time.time() - start_time
            query_times.append(execution_time)
        
        # Calculate query metrics
        total_time = sum(query_times)
        avg_time = total_time / len(query_times) if query_times else 0
        min_time = min(query_times) if query_times else 0
        max_time = max(query_times) if query_times else 0
        ops_per_sec = len(query_times) / total_time if total_time > 0 else 0
        
        query_metrics = PerformanceMetrics(
            operation_name="Transaction Queries",
            total_operations=500,
            successful_operations=successful_queries,
            failed_operations=failed_queries,
            total_time=total_time,
            min_time=min_time,
            max_time=max_time,
            avg_time=avg_time,
            operations_per_second=ops_per_sec
        )
        
        self.performance_results.append(query_metrics)
        print(f"   Query Performance: {ops_per_sec:.1f} queries/sec (avg: {avg_time*1000:.1f}ms)")
        
        # Cleanup test transactions
        print("\n[Cleanup] Removing performance test transactions...")
        cleanup_start = time.time()
        with self.data_access.get_connection() as conn:
            # Delete weight events first (foreign key constraint)
            conn.execute("""
                DELETE FROM weigh_events 
                WHERE transaction_id IN (
                    SELECT id FROM transactions WHERE vehicle_no LIKE 'PERF-TRANS-%'
                )
            """)
            
            # Delete transactions
            result = conn.execute("DELETE FROM transactions WHERE vehicle_no LIKE 'PERF-TRANS-%'")
            deleted_count = result.rowcount
        
        cleanup_time = time.time() - cleanup_start
        print(f"   Cleanup: Deleted {deleted_count} test transactions in {cleanup_time:.2f}s")
        
        # Logout
        self.auth_service.logout_current_user()
    
    def test_concurrent_operations(self):
        """Test system performance under concurrent operations"""
        
        print("📊 Testing concurrent operations performance...")
        
        # Test 1: Concurrent Database Operations
        print("\n[1/3] Concurrent Database Operations Test...")
        
        def concurrent_database_task(task_id: int) -> Dict[str, Any]:
            """Database task for concurrent execution"""
            results = {'task_id': task_id, 'operations': 0, 'errors': 0, 'time': 0}
            start_time = time.time()
            
            try:
                from database.data_access import DataAccessLayer
                from core.config import DATABASE_PATH
                db = DataAccessLayer(str(DATABASE_PATH))
                
                for i in range(10):  # 10 operations per task
                    try:
                        with db.get_connection() as conn:
                            # Mix of operations
                            if i % 3 == 0:  # Insert
                                product_id = str(uuid.uuid4())
                                conn.execute("""
                                    INSERT INTO products (id, code, name, unit, is_active, created_at_utc)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (product_id, f'CONC_{task_id}_{i}', f'Concurrent Product {task_id}_{i}', 'KG', 1, datetime.utcnow().isoformat()))
                            
                            elif i % 3 == 1:  # Select
                                conn.execute("SELECT COUNT(*) FROM products WHERE is_active = 1").fetchone()
                            
                            else:  # Update
                                conn.execute("""
                                    UPDATE products 
                                    SET description = ? 
                                    WHERE code LIKE ?
                                """, (f'Updated by task {task_id}', f'CONC_{task_id}_%'))
                        
                        results['operations'] += 1
                    except Exception:
                        results['errors'] += 1
            
            except Exception:
                results['errors'] += 10  # Mark all as failed
            
            results['time'] = time.time() - start_time
            return results
        
        # Execute concurrent database tasks
        concurrent_start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(concurrent_database_task, i) for i in range(20)]
            concurrent_results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        concurrent_time = time.time() - concurrent_start
        
        total_operations = sum(r['operations'] for r in concurrent_results)
        total_errors = sum(r['errors'] for r in concurrent_results)
        avg_task_time = sum(r['time'] for r in concurrent_results) / len(concurrent_results)
        
        print(f"   Concurrent DB Operations: {total_operations} ops in {concurrent_time:.2f}s")
        print(f"   Throughput: {total_operations/concurrent_time:.1f} ops/sec")
        print(f"   Error Rate: {total_errors}/{total_operations + total_errors} ({(total_errors/(total_operations + total_errors)*100):.1f}%)")
        
        # Test 2: Concurrent Authentication
        print("\n[2/3] Concurrent Authentication Test...")
        
        def concurrent_auth_task(task_id: int) -> Dict[str, Any]:
            """Authentication task for concurrent execution"""
            results = {'task_id': task_id, 'logins': 0, 'errors': 0, 'time': 0}
            start_time = time.time()
            
            try:
                from auth.auth_service import AuthenticationService
                auth = AuthenticationService()
                
                for i in range(5):  # 5 login/logout cycles per task
                    try:
                        session = auth.login_user("admin", "1234")
                        if session:
                            results['logins'] += 1
                            time.sleep(0.01)  # Brief session time
                            auth.logout_current_user()
                        else:
                            results['errors'] += 1
                    except Exception:
                        results['errors'] += 1
            
            except Exception:
                results['errors'] += 5
            
            results['time'] = time.time() - start_time
            return results
        
        # Execute concurrent auth tasks
        auth_start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(concurrent_auth_task, i) for i in range(15)]
            auth_results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        auth_time = time.time() - auth_start
        
        total_logins = sum(r['logins'] for r in auth_results)
        total_auth_errors = sum(r['errors'] for r in auth_results)
        
        print(f"   Concurrent Authentication: {total_logins} logins in {auth_time:.2f}s")
        print(f"   Login Throughput: {total_logins/auth_time:.1f} logins/sec")
        print(f"   Auth Error Rate: {total_auth_errors}/{total_logins + total_auth_errors} ({(total_auth_errors/(total_logins + total_auth_errors)*100) if (total_logins + total_auth_errors) > 0 else 0:.1f}%)")
        
        # Test 3: Mixed Concurrent Operations
        print("\n[3/3] Mixed Concurrent Operations Test...")
        
        def mixed_operation_task(task_id: int) -> Dict[str, Any]:
            """Mixed operations task"""
            results = {'task_id': task_id, 'total_ops': 0, 'errors': 0, 'time': 0}
            start_time = time.time()
            
            try:
                # Mix of database, auth, and other operations
                from database.data_access import DataAccessLayer
                from auth.auth_service import AuthenticationService
                from core.config import DATABASE_PATH
                
                db = DataAccessLayer(str(DATABASE_PATH))
                auth = AuthenticationService()
                
                for i in range(8):  # 8 mixed operations
                    try:
                        if i % 4 == 0:  # Database read
                            with db.get_connection() as conn:
                                conn.execute("SELECT COUNT(*) FROM transactions").fetchone()
                        
                        elif i % 4 == 1:  # Authentication check
                            session = auth.login_user("admin", "1234")
                            if session:
                                auth.logout_current_user()
                        
                        elif i % 4 == 2:  # Complex query
                            with db.get_connection() as conn:
                                conn.execute("""
                                    SELECT t.vehicle_no, COUNT(w.id) as weight_events
                                    FROM transactions t
                                    LEFT JOIN weigh_events w ON t.id = w.transaction_id
                                    GROUP BY t.id
                                    LIMIT 5
                                """).fetchall()
                        
                        else:  # Data processing simulation
                            import json
                            test_data = {'task': task_id, 'op': i, 'timestamp': datetime.now().isoformat()}
                            json.dumps(test_data)  # JSON serialization
                        
                        results['total_ops'] += 1
                    except Exception:
                        results['errors'] += 1
            
            except Exception:
                results['errors'] += 8
            
            results['time'] = time.time() - start_time
            return results
        
        # Execute mixed operations
        mixed_start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            futures = [executor.submit(mixed_operation_task, i) for i in range(25)]
            mixed_results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        mixed_time = time.time() - mixed_start
        
        total_mixed_ops = sum(r['total_ops'] for r in mixed_results)
        total_mixed_errors = sum(r['errors'] for r in mixed_results)
        
        print(f"   Mixed Operations: {total_mixed_ops} ops in {mixed_time:.2f}s")
        print(f"   Mixed Throughput: {total_mixed_ops/mixed_time:.1f} ops/sec")
        print(f"   Mixed Error Rate: {total_mixed_errors}/{total_mixed_ops + total_mixed_errors} ({(total_mixed_errors/(total_mixed_ops + total_mixed_errors)*100) if (total_mixed_ops + total_mixed_errors) > 0 else 0:.1f}%)")
        
        # Cleanup concurrent test data
        print("\n[Cleanup] Removing concurrent test data...")
        with self.data_access.get_connection() as conn:
            result = conn.execute("DELETE FROM products WHERE code LIKE 'CONC_%'")
            print(f"   Removed {result.rowcount} concurrent test products")
    
    def test_system_under_load(self):
        """Test system behavior under sustained load"""
        
        print("📊 Testing system under sustained load...")
        
        # Test 1: Sustained Database Load
        print("\n[1/2] Sustained Database Load Test (30 seconds)...")
        
        load_start = time.time()
        load_duration = 30.0  # 30 seconds
        operation_count = 0
        error_count = 0
        
        while (time.time() - load_start) < load_duration:
            try:
                with self.data_access.get_connection() as conn:
                    # Random operation
                    import random
                    op_type = random.choice(['select', 'insert', 'update'])
                    
                    if op_type == 'select':
                        conn.execute("SELECT COUNT(*) FROM products WHERE is_active = 1").fetchone()
                    
                    elif op_type == 'insert':
                        test_id = str(uuid.uuid4())
                        conn.execute("""
                            INSERT INTO products (id, code, name, unit, is_active, created_at_utc)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (test_id, f'LOAD_{operation_count}', f'Load Test Product', 'KG', 1, datetime.utcnow().isoformat()))
                    
                    else:  # update
                        conn.execute("""
                            UPDATE products 
                            SET description = ? 
                            WHERE code LIKE 'LOAD_%' 
                            LIMIT 1
                        """, (f'Updated at {datetime.now().isoformat()}',))
                
                operation_count += 1
                
            except Exception:
                error_count += 1
            
            time.sleep(0.01)  # Small delay to prevent overwhelming
        
        load_time = time.time() - load_start
        ops_per_sec = operation_count / load_time
        error_rate = (error_count / (operation_count + error_count)) * 100 if (operation_count + error_count) > 0 else 0
        
        print(f"   Sustained Load Results:")
        print(f"     Operations: {operation_count} in {load_time:.1f}s")
        print(f"     Throughput: {ops_per_sec:.1f} ops/sec")
        print(f"     Error Rate: {error_rate:.2f}%")
        
        # Test 2: Memory Usage Monitoring
        print("\n[2/2] Memory Usage Monitoring...")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create memory load
        large_data_sets = []
        for i in range(100):
            # Create some data structures
            data_set = {
                'transactions': [{'id': str(uuid.uuid4()), 'weight': 1000 + i} for _ in range(100)],
                'timestamp': datetime.now().isoformat()
            }
            large_data_sets.append(data_set)
            
            if i % 20 == 0:  # Check memory every 20 iterations
                current_memory = process.memory_info().rss / 1024 / 1024
                print(f"     Memory at iteration {i}: {current_memory:.1f} MB")
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        print(f"   Memory Usage:")
        print(f"     Initial: {initial_memory:.1f} MB")
        print(f"     Final: {final_memory:.1f} MB")
        print(f"     Increase: {memory_increase:.1f} MB")
        
        # Cleanup memory test data
        del large_data_sets
        
        # Cleanup database test data
        with self.data_access.get_connection() as conn:
            result = conn.execute("DELETE FROM products WHERE code LIKE 'LOAD_%'")
            print(f"   Cleaned up {result.rowcount} load test products")
    
    def test_system_stress(self):
        """Test system under extreme stress conditions"""
        
        print("🕰️ Testing system under stress conditions...")
        
        # Test 1: High Concurrency Stress
        print("\n[1/3] High Concurrency Stress Test...")
        
        def stress_task(task_id: int) -> Dict[str, Any]:
            """Stress test task"""
            results = {'task_id': task_id, 'operations': 0, 'errors': 0}
            
            try:
                from database.data_access import DataAccessLayer
                from core.config import DATABASE_PATH
                db = DataAccessLayer(str(DATABASE_PATH))
                
                # Rapid-fire operations
                for i in range(20):  # 20 operations per task
                    try:
                        with db.get_connection() as conn:
                            conn.execute("SELECT COUNT(*) FROM products").fetchone()
                        results['operations'] += 1
                    except Exception:
                        results['errors'] += 1
            
            except Exception:
                results['errors'] += 20
            
            return results
        
        # High concurrency test
        stress_start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:  # High thread count
            futures = [executor.submit(stress_task, i) for i in range(100)]  # Many tasks
            stress_results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        stress_time = time.time() - stress_start
        
        total_stress_ops = sum(r['operations'] for r in stress_results)
        total_stress_errors = sum(r['errors'] for r in stress_results)
        stress_error_rate = (total_stress_errors / (total_stress_ops + total_stress_errors)) * 100 if (total_stress_ops + total_stress_errors) > 0 else 0
        
        print(f"   High Concurrency Stress:")
        print(f"     Operations: {total_stress_ops} in {stress_time:.2f}s")
        print(f"     Throughput: {total_stress_ops/stress_time:.1f} ops/sec")
        print(f"     Error Rate: {stress_error_rate:.2f}%")
        
        # Test 2: Resource Exhaustion Test
        print("\n[2/3] Resource Exhaustion Test...")
        
        # Create many database connections rapidly
        connection_count = 0
        connection_errors = 0
        
        for i in range(200):  # Try to create many connections
            try:
                with self.data_access.get_connection() as conn:
                    conn.execute("SELECT 1").fetchone()
                connection_count += 1
            except Exception:
                connection_errors += 1
        
        print(f"   Connection Stress: {connection_count} successful, {connection_errors} failed")
        
        # Test 3: Large Data Processing
        print("\n[3/3] Large Data Processing Test...")
        
        # Create large dataset in memory and process it
        large_dataset_start = time.time()
        
        try:
            # Create large transaction dataset
            large_transactions = []
            for i in range(10000):  # 10,000 fake transactions
                transaction = {
                    'id': str(uuid.uuid4()),
                    'vehicle_no': f'STRESS-{i:05d}',
                    'timestamp': datetime.now().isoformat(),
                    'weight_events': [
                        {'weight': 1500.0 + (i % 1000), 'stable': True},
                        {'weight': 2500.0 + (i % 1000), 'stable': True}
                    ],
                    'net_weight': 1000.0 + (i % 1000)
                }
                large_transactions.append(transaction)
            
            # Process the dataset
            processed_count = 0
            total_weight = 0.0
            
            for transaction in large_transactions:
                try:
                    # Simulate processing
                    total_weight += transaction['net_weight']
                    processed_count += 1
                except Exception:
                    pass
            
            processing_time = time.time() - large_dataset_start
            processing_rate = processed_count / processing_time
            
            print(f"   Large Data Processing:")
            print(f"     Records Processed: {processed_count:,}")
            print(f"     Processing Time: {processing_time:.2f}s")
            print(f"     Processing Rate: {processing_rate:.1f} records/sec")
            print(f"     Total Weight Processed: {total_weight:,.1f} kg")
            
            # Cleanup
            del large_transactions
            
        except MemoryError:
            print("   Memory limit reached during large data test")
        except Exception as e:
            print(f"   Large data processing error: {e}")
    
    def test_resource_usage(self):
        """Test memory and resource usage"""
        
        print("📈 Testing memory and resource usage...")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Initial resource measurements
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        initial_cpu = process.cpu_percent()
        
        print(f"   Initial Resources:")
        print(f"     Memory: {initial_memory:.1f} MB")
        print(f"     CPU: {initial_cpu:.1f}%")
        
        # Resource usage during operations
        print("\n   Testing resource usage during intensive operations...")
        
        # Simulate intensive database operations
        resource_test_start = time.time()
        
        for i in range(1000):
            try:
                with self.data_access.get_connection() as conn:
                    # Multiple queries per iteration
                    conn.execute("SELECT COUNT(*) FROM products").fetchone()
                    conn.execute("SELECT COUNT(*) FROM parties").fetchone()
                    conn.execute("SELECT COUNT(*) FROM transactions").fetchone()
                
                # Check resources every 100 iterations
                if i % 100 == 0 and i > 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    current_cpu = process.cpu_percent()
                    print(f"     Iteration {i}: Memory {current_memory:.1f} MB, CPU {current_cpu:.1f}%")
            
            except Exception:
                pass
        
        resource_test_time = time.time() - resource_test_start
        
        # Final resource measurements
        final_memory = process.memory_info().rss / 1024 / 1024
        final_cpu = process.cpu_percent()
        
        memory_increase = final_memory - initial_memory
        
        print(f"\n   Final Resource Usage:")
        print(f"     Memory: {final_memory:.1f} MB (increase: {memory_increase:.1f} MB)")
        print(f"     CPU: {final_cpu:.1f}%")
        print(f"     Test Duration: {resource_test_time:.2f}s")
        print(f"     Operations Rate: {1000/resource_test_time:.1f} ops/sec")
        
        # Memory leak detection
        if memory_increase > 50:  # More than 50MB increase
            print(f"   ⚠️  Potential memory leak detected: {memory_increase:.1f} MB increase")
        else:
            print(f"   ✅ Memory usage appears stable")
    
    def generate_performance_report(self) -> bool:
        """Generate comprehensive performance report"""
        
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print("   PERFORMANCE & STRESS TEST SUITE - FINAL REPORT")
        print("=" * 80)
        
        print(f"📉 PERFORMANCE SUMMARY:")
        print(f"   Test Duration: {total_duration:.1f} seconds")
        print(f"   Total Metrics: {len(self.performance_results)}")
        
        if not self.performance_results:
            print("   ⚠️ No performance metrics collected")
            return False
        
        # Performance metrics summary
        print(f"\n📊 DETAILED PERFORMANCE METRICS:")
        print(f"{'Operation':<30} {'Ops/Sec':<12} {'Avg Time':<12} {'Success Rate':<12}")
        print("-" * 68)
        
        for metric in self.performance_results:
            avg_time_ms = metric.avg_time * 1000
            print(f"{metric.operation_name:<30} {metric.operations_per_second:<12.1f} {avg_time_ms:<12.1f}ms {metric.success_rate:<12.1f}%")
        
        # Performance analysis
        print(f"\n🔍 PERFORMANCE ANALYSIS:")
        
        # Find best and worst performing operations
        best_throughput = max(self.performance_results, key=lambda m: m.operations_per_second)
        worst_throughput = min(self.performance_results, key=lambda m: m.operations_per_second)
        
        print(f"   Best Throughput:  {best_throughput.operation_name} ({best_throughput.operations_per_second:.1f} ops/sec)")
        print(f"   Worst Throughput: {worst_throughput.operation_name} ({worst_throughput.operations_per_second:.1f} ops/sec)")
        
        # Find fastest and slowest operations
        fastest_operation = min(self.performance_results, key=lambda m: m.avg_time)
        slowest_operation = max(self.performance_results, key=lambda m: m.avg_time)
        
        print(f"   Fastest Operation: {fastest_operation.operation_name} ({fastest_operation.avg_time*1000:.1f}ms avg)")
        print(f"   Slowest Operation: {slowest_operation.operation_name} ({slowest_operation.avg_time*1000:.1f}ms avg)")
        
        # Success rate analysis
        avg_success_rate = sum(m.success_rate for m in self.performance_results) / len(self.performance_results)
        low_success_operations = [m for m in self.performance_results if m.success_rate < 95.0]
        
        print(f"   Average Success Rate: {avg_success_rate:.1f}%")
        
        if low_success_operations:
            print(f"   ⚠️ Operations with low success rate:")
            for op in low_success_operations:
                print(f"     - {op.operation_name}: {op.success_rate:.1f}%")
        
        # Performance benchmarks
        print(f"\n🎯 PERFORMANCE BENCHMARKS:")
        
        benchmarks = {
            'Database Operations': {'min_ops_sec': 100, 'max_avg_time_ms': 50},
            'Authentication': {'min_ops_sec': 50, 'max_avg_time_ms': 100},
            'Weight Readings': {'min_ops_sec': 500, 'max_avg_time_ms': 10},
            'Transaction Processing': {'min_ops_sec': 20, 'max_avg_time_ms': 200}
        }
        
        benchmark_results = []
        for metric in self.performance_results:
            for bench_name, bench_criteria in benchmarks.items():
                if bench_name.lower() in metric.operation_name.lower():
                    meets_throughput = metric.operations_per_second >= bench_criteria['min_ops_sec']
                    meets_latency = metric.avg_time * 1000 <= bench_criteria['max_avg_time_ms']
                    
                    status = "✅" if (meets_throughput and meets_latency) else "❌"
                    benchmark_results.append((metric.operation_name, status, meets_throughput, meets_latency))
                    
                    print(f"   {status} {metric.operation_name}")
                    if not meets_throughput:
                        print(f"       Throughput: {metric.operations_per_second:.1f} < {bench_criteria['min_ops_sec']} ops/sec")
                    if not meets_latency:
                        print(f"       Latency: {metric.avg_time*1000:.1f} > {bench_criteria['max_avg_time_ms']}ms")
        
        # Overall performance verdict
        passed_benchmarks = sum(1 for _, status, _, _ in benchmark_results if status == "✅")
        total_benchmarks = len(benchmark_results)
        
        print(f"\n🎆 OVERALL PERFORMANCE VERDICT:")
        
        if total_benchmarks == 0:
            print("   ⚠️ No benchmarks could be evaluated")
            verdict = False
        elif passed_benchmarks >= total_benchmarks * 0.8:  # 80% pass rate
            print(f"   ✅ EXCELLENT PERFORMANCE")
            print(f"   🎉 {passed_benchmarks}/{total_benchmarks} benchmarks passed ({(passed_benchmarks/total_benchmarks*100):.1f}%)")
            print(f"   💯 System is ready for production workloads")
            verdict = True
        elif passed_benchmarks >= total_benchmarks * 0.6:  # 60% pass rate
            print(f"   ⚠️ ACCEPTABLE PERFORMANCE")
            print(f"   🔧 {total_benchmarks - passed_benchmarks} performance issues need attention")
            print(f"   📈 System can handle moderate workloads")
            verdict = True
        else:
            print(f"   ❌ POOR PERFORMANCE")
            print(f"   🛠️  {total_benchmarks - passed_benchmarks} critical performance issues")
            print(f"   ⚠️ System may struggle under production load")
            verdict = False
        
        print(f"\n🏁 Performance Testing Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        return verdict

def main():
    """Main performance test execution function"""
    performance_suite = PerformanceTestSuite()
    
    try:
        success = performance_suite.run_performance_test_suite()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⚠️ Performance test suite interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: Performance test suite crashed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
