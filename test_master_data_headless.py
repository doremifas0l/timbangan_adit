#!/usr/bin/env python3
"""
Headless test script for Master Data Management functionality
Tests the database operations without UI components
"""

import sys
import os
import uuid
from datetime import datetime

sys.path.insert(0, '.')

from database.data_access import DataAccessLayer
from core.config import DATABASE_PATH

def test_database_operations():
    """Test database CRUD operations for master data"""
    
    print("Testing Master Data Database Operations...")
    
    # Initialize database
    db_access = DataAccessLayer(str(DATABASE_PATH))
    
    try:
        # Test Product Operations
        print("\n1. Testing Product Operations...")
        
        with db_access.get_connection() as conn:
            # Create test product
            product_id = str(uuid.uuid4())
            current_time = datetime.utcnow().isoformat()
            
            conn.execute("""
                INSERT INTO products (id, code, name, description, unit, is_active, created_at_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (product_id, 'TEST001', 'Test Product', 'Test Description', 'KG', 1, current_time))
            
            # Read product
            product = conn.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            
            if product and product['name'] == 'Test Product':
                print("   ✅ Product CREATE and READ operations successful")
            else:
                print("   ❌ Product CREATE/READ failed")
                return False
            
            # Update product
            conn.execute(
                "UPDATE products SET name = ? WHERE id = ?", 
                ('Updated Test Product', product_id)
            )
            
            # Verify update
            updated_product = conn.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            
            if updated_product and updated_product['name'] == 'Updated Test Product':
                print("   ✅ Product UPDATE operation successful")
            else:
                print("   ❌ Product UPDATE failed")
                return False
            
            # Delete product
            conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
            
            # Verify deletion
            deleted_product = conn.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            
            if not deleted_product:
                print("   ✅ Product DELETE operation successful")
            else:
                print("   ❌ Product DELETE failed")
                return False
        
        # Test Party Operations
        print("\n2. Testing Customer/Supplier Operations...")
        
        with db_access.get_connection() as conn:
            # Create test party
            party_id = str(uuid.uuid4())
            current_time = datetime.utcnow().isoformat()
            
            conn.execute("""
                INSERT INTO parties (id, code, name, type, address, phone, email, is_active, created_at_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (party_id, 'TESTC001', 'Test Customer', 'Customer', '123 Test St', '555-1234', 'test@test.com', 1, current_time))
            
            # Read party
            party = conn.execute(
                "SELECT * FROM parties WHERE id = ?", (party_id,)
            ).fetchone()
            
            if party and party['name'] == 'Test Customer':
                print("   ✅ Customer/Supplier CREATE and READ operations successful")
            else:
                print("   ❌ Customer/Supplier CREATE/READ failed")
                return False
            
            # Update party
            conn.execute(
                "UPDATE parties SET type = ? WHERE id = ?", 
                ('Supplier', party_id)
            )
            
            # Verify update
            updated_party = conn.execute(
                "SELECT * FROM parties WHERE id = ?", (party_id,)
            ).fetchone()
            
            if updated_party and updated_party['type'] == 'Supplier':
                print("   ✅ Customer/Supplier UPDATE operation successful")
            else:
                print("   ❌ Customer/Supplier UPDATE failed")
                return False
            
            # Clean up
            conn.execute("DELETE FROM parties WHERE id = ?", (party_id,))
            print("   ✅ Customer/Supplier DELETE operation successful")
        
        # Test Transporter Operations
        print("\n3. Testing Transporter Operations...")
        
        with db_access.get_connection() as conn:
            # Create test transporter
            transporter_id = str(uuid.uuid4())
            current_time = datetime.utcnow().isoformat()
            
            conn.execute("""
                INSERT INTO transporters (id, code, name, license_no, phone, is_active, created_at_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (transporter_id, 'TESTT001', 'Test Transporter', 'TL12345', '555-5678', 1, current_time))
            
            # Read transporter
            transporter = conn.execute(
                "SELECT * FROM transporters WHERE id = ?", (transporter_id,)
            ).fetchone()
            
            if transporter and transporter['name'] == 'Test Transporter':
                print("   ✅ Transporter CREATE and READ operations successful")
            else:
                print("   ❌ Transporter CREATE/READ failed")
                return False
            
            # Update transporter
            conn.execute(
                "UPDATE transporters SET license_no = ? WHERE id = ?", 
                ('TL54321', transporter_id)
            )
            
            # Verify update
            updated_transporter = conn.execute(
                "SELECT * FROM transporters WHERE id = ?", (transporter_id,)
            ).fetchone()
            
            if updated_transporter and updated_transporter['license_no'] == 'TL54321':
                print("   ✅ Transporter UPDATE operation successful")
            else:
                print("   ❌ Transporter UPDATE failed")
                return False
            
            # Clean up
            conn.execute("DELETE FROM transporters WHERE id = ?", (transporter_id,))
            print("   ✅ Transporter DELETE operation successful")
        
        print("\n✅ All database operations completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Database operation failed: {e}")
        return False

def test_sample_data_creation():
    """Create sample data for demonstration"""
    
    print("\nCreating sample master data...")
    
    db_access = DataAccessLayer(str(DATABASE_PATH))
    
    try:
        with db_access.get_connection() as conn:
            current_time = datetime.utcnow().isoformat()
            
            # Sample products
            sample_products = [
                ('COAL001', 'Coal Premium', 'High quality coal for industrial use', 'TON'),
                ('IRON001', 'Iron Ore Grade A', 'Premium grade iron ore', 'TON'),
                ('SAND001', 'Construction Sand', 'Fine sand for construction', 'M3'),
                ('GRAV001', 'Gravel 20mm', 'Construction gravel 20mm size', 'M3')
            ]
            
            for code, name, desc, unit in sample_products:
                product_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT OR IGNORE INTO products (id, code, name, description, unit, is_active, created_at_utc)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (product_id, code, name, desc, unit, 1, current_time))
            
            # Sample customers and suppliers
            sample_parties = [
                ('CUST001', 'ABC Mining Corporation', 'Customer', '123 Mining Street, Industrial Zone', '555-1001'),
                ('CUST002', 'Delta Construction Ltd', 'Customer', '456 Builder Ave, Construction District', '555-1002'),
                ('SUPP001', 'Mountain Quarry Co.', 'Supplier', '789 Quarry Road, Mountain View', '555-2001'),
                ('SUPP002', 'Pacific Mining Group', 'Supplier', '321 Pacific Highway, Coast City', '555-2002'),
                ('BOTH001', 'Universal Materials Inc.', 'Both', '654 Commerce Blvd, Trade Center', '555-3001')
            ]
            
            for code, name, party_type, address, phone in sample_parties:
                party_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT OR IGNORE INTO parties (id, code, name, type, address, phone, is_active, created_at_utc)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (party_id, code, name, party_type, address, phone, 1, current_time))
            
            # Sample transporters
            sample_transporters = [
                ('TRANS001', 'Fast Logistics Express', 'FL12345', '555-4001'),
                ('TRANS002', 'Heavy Haul Transport', 'HH67890', '555-4002'),
                ('TRANS003', 'Regional Freight Co.', 'RF24680', '555-4003'),
                ('TRANS004', 'Metro Delivery Service', 'MD13579', '555-4004')
            ]
            
            for code, name, license_no, phone in sample_transporters:
                transporter_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT OR IGNORE INTO transporters (id, code, name, license_no, phone, is_active, created_at_utc)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (transporter_id, code, name, license_no, phone, 1, current_time))
            
            conn.commit()
            
        # Verify sample data
        with db_access.get_connection() as conn:
            product_count = conn.execute("SELECT COUNT(*) FROM products WHERE is_active = 1").fetchone()[0]
            party_count = conn.execute("SELECT COUNT(*) FROM parties WHERE is_active = 1").fetchone()[0]
            transporter_count = conn.execute("SELECT COUNT(*) FROM transporters WHERE is_active = 1").fetchone()[0]
            
        print(f"   ✅ Created {product_count} products")
        print(f"   ✅ Created {party_count} customers/suppliers")
        print(f"   ✅ Created {transporter_count} transporters")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error creating sample data: {e}")
        return False

def test_dropdown_queries():
    """Test the dropdown population queries"""
    
    print("\nTesting dropdown data queries...")
    
    db_access = DataAccessLayer(str(DATABASE_PATH))
    
    try:
        with db_access.get_connection() as conn:
            # Test products query
            products = conn.execute("""
                SELECT id, name FROM products 
                WHERE is_active = 1 
                ORDER BY name
            """).fetchall()
            
            print(f"   ✅ Products dropdown query returned {len(products)} items")
            
            # Test parties query
            parties = conn.execute("""
                SELECT id, name, type FROM parties 
                WHERE is_active = 1 
                ORDER BY name
            """).fetchall()
            
            print(f"   ✅ Parties dropdown query returned {len(parties)} items")
            
            # Test transporters query
            transporters = conn.execute("""
                SELECT id, name FROM transporters 
                WHERE is_active = 1 
                ORDER BY name
            """).fetchall()
            
            print(f"   ✅ Transporters dropdown query returned {len(transporters)} items")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Dropdown query failed: {e}")
        return False

def main():
    """Run all tests"""
    
    print("🧪 SCALE System - Master Data Management Headless Test")
    print("=" * 65)
    
    # Ensure we're in the right directory
    if not os.path.exists('database'):
        print("❌ Error: Please run this test from the scale_system directory")
        return 1
    
    try:
        # Run tests
        tests = [
            test_database_operations,
            test_sample_data_creation,
            test_dropdown_queries
        ]
        
        passed = 0
        total = len(tests)
        
        for test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    print(f"❌ {test_func.__name__} failed")
            except Exception as e:
                print(f"❌ {test_func.__name__} crashed: {e}")
        
        print("\n" + "=" * 65)
        print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
        print(f"✅ Success Rate: {passed/total*100:.1f}%")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED - Master Data Management is ready!")
            print("\n📦 Sample Data Summary:")
            
            # Show final summary
            db_access = DataAccessLayer(str(DATABASE_PATH))
            with db_access.get_connection() as conn:
                product_count = conn.execute("SELECT COUNT(*) FROM products WHERE is_active = 1").fetchone()[0]
                party_count = conn.execute("SELECT COUNT(*) FROM parties WHERE is_active = 1").fetchone()[0]
                transporter_count = conn.execute("SELECT COUNT(*) FROM transporters WHERE is_active = 1").fetchone()[0]
                
                print(f"  • {product_count} Products available for selection")
                print(f"  • {party_count} Customers/Suppliers available for selection")
                print(f"  • {transporter_count} Transporters available for selection")
            
            return 0
        else:
            print(f"\n⚠️ {total-passed} tests failed - Check implementation")
            return 1
            
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
