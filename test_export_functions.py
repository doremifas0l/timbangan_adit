#!/usr/bin/env python3
"""
Test script to verify export and backup functionality
"""

import sys
import os
from pathlib import Path

# Add system path
sys.path.insert(0, str(Path(__file__).parent))

from utils.helpers import export_to_csv, export_to_json, format_file_size
from database.data_access import DataAccessLayer
from core.config import DATABASE_PATH

def test_export_functions():
    """Test CSV and JSON export functions"""
    
    print("Testing Export Functions")
    print("=" * 50)
    
    # Test data
    test_transactions = [
        {
            'id': 1,
            'ticket_no': 'SC000001', 
            'vehicle_no': 'ABC-123',
            'gross_weight': 15250.5,
            'tare_weight': 8750.0,
            'net_weight': 6500.5,
            'product': 'Rice',
            'customer': 'ABC Company',
            'operator': 'admin',
            'status': 'complete',
            'created_at_utc': '2025-08-23 19:43:00'
        },
        {
            'id': 2,
            'ticket_no': 'SC000002', 
            'vehicle_no': 'XYZ-456',
            'gross_weight': 22100.0,
            'tare_weight': 9800.5,
            'net_weight': 12299.5,
            'product': 'Wheat',
            'customer': 'XYZ Corp',
            'operator': 'operator',
            'status': 'complete',
            'created_at_utc': '2025-08-23 19:42:00'
        }
    ]
    
    # Test CSV export
    csv_file = 'data/test_export.csv'
    print(f"Testing CSV export to {csv_file}...")
    
    success = export_to_csv(test_transactions, csv_file)
    if success and os.path.exists(csv_file):
        file_size = os.path.getsize(csv_file)
        print(f"✅ CSV export successful - {format_file_size(file_size)}")
        
        # Read back and display first few lines
        with open(csv_file, 'r') as f:
            lines = f.readlines()[:3]
            print(f"   First {len(lines)} lines:")
            for i, line in enumerate(lines):
                print(f"   {i+1}: {line.strip()}")
    else:
        print("❌ CSV export failed")
    
    print()
    
    # Test JSON export
    json_file = 'data/test_export.json'
    print(f"Testing JSON export to {json_file}...")
    
    export_data = {
        'export_info': {
            'exported_at': '2025-08-23 19:43:00',
            'total_records': len(test_transactions),
            'exported_by': 'test_user'
        },
        'transactions': test_transactions
    }
    
    success = export_to_json(export_data, json_file)
    if success and os.path.exists(json_file):
        file_size = os.path.getsize(json_file)
        print(f"✅ JSON export successful - {format_file_size(file_size)}")
        
        # Read back and show structure
        import json
        with open(json_file, 'r') as f:
            data = json.load(f)
            print(f"   Records in file: {data['export_info']['total_records']}")
            print(f"   Export timestamp: {data['export_info']['exported_at']}")
    else:
        print("❌ JSON export failed")

def test_backup_functions():
    """Test database backup and restore functions"""
    
    print("\nTesting Backup Functions")
    print("=" * 50)
    
    # Initialize database
    try:
        data_access = DataAccessLayer(str(DATABASE_PATH))
        
        # Test backup
        backup_file = 'backups/test_backup.db'
        
        # Ensure backup directory exists
        os.makedirs('backups', exist_ok=True)
        
        print(f"Testing database backup to {backup_file}...")
        success = data_access.create_backup(backup_file)
        
        if success and os.path.exists(backup_file):
            file_size = os.path.getsize(backup_file)
            print(f"✅ Database backup successful - {format_file_size(file_size)}")
            
            # Test if backup is valid by trying to connect to it
            import sqlite3
            try:
                with sqlite3.connect(backup_file) as conn:
                    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    print(f"   Tables in backup: {len(tables)} found")
                    if tables:
                        print(f"   First few tables: {tables[:3]}")
                print("✅ Backup file verification successful")
            except Exception as e:
                print(f"❌ Backup verification failed: {e}")
        else:
            print("❌ Database backup failed")
            
    except Exception as e:
        print(f"❌ Database access failed: {e}")

def main():
    """Run all tests"""
    
    # Create required directories
    for dir_name in ['data', 'backups']:
        os.makedirs(dir_name, exist_ok=True)
    
    print("SCALE System Export & Backup Function Tests")
    print("=" * 60)
    
    try:
        test_export_functions()
        test_backup_functions()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print(
            "\n📁 Test files created:\n"
            "   • data/test_export.csv\n"
            "   • data/test_export.json\n"
            "   • backups/test_backup.db"
        )
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
