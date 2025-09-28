#!/usr/bin/env python3
"""
Database Initialization Script
Ensures the database is properly set up with the correct schema and default data.
"""

import sys
import os
import sqlite3
from pathlib import Path

# Add the scale_system directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def initialize_database():
    """Initialize the database with proper schema and test data"""
    try:
        from database.schema import DatabaseSchema
        from core.config import DATABASE_PATH
        
        print(f"Initializing database at: {DATABASE_PATH}")
        
        # Ensure the parent directory exists
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize schema
        schema = DatabaseSchema(str(DATABASE_PATH))
        schema.initialize_database()

        print("[PASS] Database schema creation process completed.")

        # Verify table creation
        with sqlite3.connect(DATABASE_PATH) as conn:
            tables_cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            table_names = [row[0] for row in tables_cursor.fetchall()]
            print(f"Tables found: {table_names}")
            
            required_tables = ['products', 'parties', 'transporters', 'users', 'transactions']
            missing_tables = [t for t in required_tables if t not in table_names]
            
            if not missing_tables:
                 print("[PASS] All required master data and transaction tables are present.")
            else:
                 print(f"[FAIL] Missing required tables: {missing_tables}")
                 return False

        print("[PASS] Database initialization complete")
        return True
        
    except Exception as e:
        print(f"[FAIL] Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("SCALE System - Database Initialization")
    print("=" * 50)
    
    if initialize_database():
        print("\n[SUCCESS] Database is ready for use.")
        sys.exit(0)
    else:
        print("\n[FAIL] Database initialization failed.")
        sys.exit(1)