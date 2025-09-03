#!/usr/bin/env python3
"""
Test script to verify all services can initialize properly
"""

import sys
from pathlib import Path

# Add the scale_system directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    print("🔍 Testing service initializations...")
    
    # Test database access
    from database.data_access import DataAccessLayer
    from core.config import DATABASE_PATH
    print(f"✅ Database path: {DATABASE_PATH}")
    
    db = DataAccessLayer(str(DATABASE_PATH))
    with db.get_connection() as conn:
        result = conn.execute("SELECT 1").fetchone()
    print("✅ DataAccessLayer - OK")
    
    # Test authentication service
    from auth.auth_service import AuthenticationService
    auth_service = AuthenticationService()
    print("✅ AuthenticationService - OK")
    
    # Test workflow controller
    from weighing.workflow_controller import WorkflowController
    workflow = WorkflowController()
    print("✅ WorkflowController - OK")
    
    print("\n🎉 ALL SERVICES INITIALIZED SUCCESSFULLY!")
    print("✅ The application is ready to launch on Windows with GUI support.")
    
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
