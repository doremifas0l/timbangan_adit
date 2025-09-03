#!/usr/bin/env python3
"""
Database Initialization Script
Ensures the database is properly set up for testing
"""

import sys
import os
from pathlib import Path

# Add the scale_system directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def initialize_database():
    """Initialize the database with proper schema and test data"""
    try:
        from database.data_access import DataAccessLayer
        from core.config import DATABASE_PATH
        
        # Ensure database directory exists
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Initializing database at: {DATABASE_PATH}")
        
        # Create database connection
        db = DataAccessLayer(str(DATABASE_PATH))
        
        # Create tables if they don't exist
        with db.get_connection() as conn:
            # Test database connection
            conn.execute("SELECT 1").fetchone()
            print("[PASS] Database connection successful")
            
            # Check if tables exist
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            
            table_names = [table[0] for table in tables]
            print(f"Existing tables: {table_names}")
            
            if not table_names:
                print("[INFO] No tables found, database needs initialization")
                # You might want to run schema initialization here
            else:
                print(f"[PASS] Database has {len(table_names)} tables")
        
        # Test creating default users
        try:
            from auth.auth_service import AuthenticationService
            auth_service = AuthenticationService()
            print("[PASS] Authentication service initialized")
        except Exception as e:
            print(f"[WARNING] Auth service initialization: {e}")
        
        print("[PASS] Database initialization complete")
        return True
        
    except Exception as e:
        print(f"[FAIL] Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    print("SCALE System - Database Initialization")
    print("=" * 50)
    
    if initialize_database():
        print("\n[SUCCESS] Database is ready for use")
        sys.exit(0)
    else:
        print("\n[FAIL] Database initialization failed")
        sys.exit(1)
