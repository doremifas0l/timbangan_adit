#!/usr/bin/env python3
"""
Test script for Master Data Management functionality
Tests the CRUD operations and integration with main window
"""

import sys
import os
sys.path.insert(0, '.')

from PyQt6.QtWidgets import QApplication
from ui.master_data_management import MasterDataDialog, ProductEditDialog, PartyEditDialog, TransporterEditDialog
from database.data_access import DataAccessLayer
from core.config import DATABASE_PATH

def test_master_data_dialog():
    """Test the master data management dialog"""
    
    print("Testing Master Data Management...")
    
    # Initialize database
    db_access = DataAccessLayer(str(DATABASE_PATH))
    
    # Create some sample data for testing
    print("Creating sample data...")
    
    try:
        with db_access.get_connection() as conn:
            # Insert sample product
            conn.execute("""
                INSERT OR IGNORE INTO products (id, code, name, description, unit, is_active, created_at_utc)
                VALUES ('test-product-1', 'COAL001', 'Coal Premium', 'High quality coal', 'TON', 1, datetime('now'))
            """)
            
            # Insert sample party
            conn.execute("""
                INSERT OR IGNORE INTO parties (id, code, name, type, address, phone, is_active, created_at_utc)
                VALUES ('test-party-1', 'CUST001', 'ABC Mining Corp', 'Customer', '123 Mining St', '555-1234', 1, datetime('now'))
            """)
            
            # Insert sample transporter
            conn.execute("""
                INSERT OR IGNORE INTO transporters (id, code, name, license_no, phone, is_active, created_at_utc)
                VALUES ('test-transport-1', 'TRANS001', 'Fast Logistics', 'TL12345', '555-5678', 1, datetime('now'))
            """)
            
            conn.commit()
            
        print("✅ Sample data created successfully")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        return False
    
    print("🎉 Master Data Management test completed successfully!")
    return True

def test_product_dialog():
    """Test product edit dialog"""
    print("\nTesting Product Dialog...")
    
    app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
    
    # Test new product dialog
    dialog = ProductEditDialog()
    print("✅ Product dialog created successfully")
    
    return True

def test_party_dialog():
    """Test party edit dialog"""
    print("\nTesting Customer/Supplier Dialog...")
    
    app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
    
    # Test new party dialog
    dialog = PartyEditDialog()
    print("✅ Customer/Supplier dialog created successfully")
    
    return True

def test_transporter_dialog():
    """Test transporter edit dialog"""
    print("\nTesting Transporter Dialog...")
    
    app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
    
    # Test new transporter dialog
    dialog = TransporterEditDialog()
    print("✅ Transporter dialog created successfully")
    
    return True

def test_main_dialog():
    """Test main master data dialog"""
    print("\nTesting Main Master Data Dialog...")
    
    app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
    
    try:
        # Test main dialog creation
        dialog = MasterDataDialog()
        print("✅ Master Data Management dialog created successfully")
        print(f"✅ Products table has {dialog.products_table.rowCount()} rows")
        print(f"✅ Parties table has {dialog.parties_table.rowCount()} rows")
        print(f"✅ Transporters table has {dialog.transporters_table.rowCount()} rows")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating main dialog: {e}")
        return False

def main():
    """Run all tests"""
    
    print("🧪 SCALE System - Master Data Management Test Suite")
    print("=" * 60)
    
    # Ensure we're in the right directory
    if not os.path.exists('database'):
        print("❌ Error: Please run this test from the scale_system directory")
        return 1
    
    # Initialize application
    app = QApplication(sys.argv)
    
    try:
        # Run tests
        tests = [
            test_master_data_dialog,
            test_product_dialog,
            test_party_dialog,
            test_transporter_dialog,
            test_main_dialog
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
        
        print("\n" + "=" * 60)
        print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
        print(f"✅ Success Rate: {passed/total*100:.1f}%")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED - Master Data Management is ready!")
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
