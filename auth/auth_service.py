# Authentication service - integrates all auth components
from typing import Optional, Dict, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal

from .login_manager import LoginManager
from .session_manager import SessionManager, UserSession
from .rbac import RoleBasedAccessControl, Permission, Role
from database.data_access import DataAccessLayer
from core.config import DATABASE_PATH

class AuthenticationService(QObject):
    """Central authentication service for the SCALE system"""
    
    # Signals
    session_started = pyqtSignal(dict)  # Emitted when session starts
    session_ended = pyqtSignal(str)     # Emitted when session ends
    permission_denied = pyqtSignal(str) # Emitted when permission denied
    
    def __init__(self):
        super().__init__()
        
        # Initialize database schema if needed
        self._ensure_database_schema()
        
        self.db_manager = DataAccessLayer(str(DATABASE_PATH))
        self.login_manager = LoginManager(self.db_manager)
        self.session_manager = SessionManager()
        self.rbac = RoleBasedAccessControl()
        
        # Initialize default users if needed
        self.ensure_default_users()
    
    def _ensure_database_schema(self):
        """Ensure database schema is initialized"""
        try:
            from ..database.schema import DatabaseSchema
            schema = DatabaseSchema(str(DATABASE_PATH))
            schema.initialize_database()
        except Exception as e:
            print(f"Database schema initialization warning: {e}")
        
    def ensure_default_users(self):
        """Create default users if they don't exist"""
        try:
            # Check if any users exist
            users = self.login_manager.get_all_users()
            
            if not users:
                print("No users found. Creating default users...")
                
                # Create default admin user
                self.login_manager.create_user(
                    username="admin",
                    pin="1234",
                    role="Admin",
                    created_by="system"
                )
                
                # Create default supervisor
                self.login_manager.create_user(
                    username="supervisor",
                    pin="2345",
                    role="Supervisor",
                    created_by="system"
                )
                
                # Create default operator
                self.login_manager.create_user(
                    username="operator",
                    pin="3456",
                    role="Operator",
                    created_by="system"
                )
                
                print("Default users created successfully")
                print("Default credentials:")
                print("  Admin: admin / 1234")
                print("  Supervisor: supervisor / 2345")
                print("  Operator: operator / 3456")
                
        except Exception as e:
            print(f"Error ensuring default users: {e}")
    
    def authenticate(self, username: str, pin: str) -> bool:
        """Authenticate user and start session"""
        try:
            user_info = self.login_manager.authenticate_user(username, pin)
            
            if user_info:
                session = self.session_manager.create_session(user_info)
                self.session_started.emit(user_info)
                return True
                
            return False
            
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    def logout(self):
        """End current session"""
        session = self.session_manager.get_current_session()
        if session:
            username = session.username
            self.session_manager.logout()
            self.session_ended.emit(username)
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current authenticated user"""
        return self.session_manager.get_current_user()
    
    def get_current_session(self) -> Optional[UserSession]:
        """Get current session"""
        return self.session_manager.get_current_session()
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return not self.session_manager.require_authentication()
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if current user has specific permission"""
        user = self.get_current_user()
        if not user:
            return False
            
        return self.rbac.has_permission(user['role'], permission)
    
    def can_perform_action(self, action: str) -> bool:
        """Check if current user can perform specific action"""
        user = self.get_current_user()
        if not user:
            return False
            
        return self.rbac.can_perform_action(user['role'], action)
    
    def require_permission(self, permission: Permission) -> bool:
        """Require specific permission, emit signal if denied"""
        if self.has_permission(permission):
            return True
            
        user = self.get_current_user()
        if user:
            message = f"Permission denied: {permission.value} (Role: {user['role']})"
        else:
            message = "Authentication required"
            
        self.permission_denied.emit(message)
        return False
    
    def require_role(self, min_role: str) -> bool:
        """Require minimum role level"""
        user = self.get_current_user()
        if not user:
            self.permission_denied.emit("Authentication required")
            return False
            
        role_hierarchy = {
            'Operator': 1,
            'Supervisor': 2,
            'Admin': 3
        }
        
        current_level = role_hierarchy.get(user['role'], 0)
        required_level = role_hierarchy.get(min_role, 0)
        
        if current_level >= required_level:
            return True
            
        message = f"Insufficient privileges: {min_role} or higher required (Current: {user['role']})"
        self.permission_denied.emit(message)
        return False
    
    def get_accessible_features(self) -> Dict[str, list]:
        """Get features accessible to current user"""
        user = self.get_current_user()
        if not user:
            return {}
            
        return self.rbac.get_accessible_features(user['role'])
    
    def update_activity(self):
        """Update user activity timestamp"""
        self.session_manager.update_activity()
    
    def extend_session(self):
        """Extend current session"""
        self.session_manager.extend_session()
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return self.session_manager.get_session_info()
    
    def create_user(self, username: str, pin: str, role: str) -> bool:
        """Create new user (Admin only)"""
        if not self.require_role("Admin"):
            return False
            
        current_user = self.get_current_user()
        created_by = current_user['username'] if current_user else "system"
        
        return self.login_manager.create_user(username, pin, role, created_by)
    
    def change_user_pin(self, username: str, old_pin: str, new_pin: str) -> bool:
        """Change user PIN"""
        current_user = self.get_current_user()
        if not current_user:
            return False
            
        # Users can change their own PIN, Admins can change any PIN
        if current_user['username'] != username and current_user['role'] != 'Admin':
            self.permission_denied.emit("Cannot change PIN for other users")
            return False
            
        return self.login_manager.change_user_pin(
            username, old_pin, new_pin, current_user['username']
        )
    
    def deactivate_user(self, username: str, reason: str) -> bool:
        """Deactivate user (Admin only)"""
        if not self.require_role("Admin"):
            return False
            
        current_user = self.get_current_user()
        deactivated_by = current_user['username'] if current_user else "system"
        
        return self.login_manager.deactivate_user(username, deactivated_by, reason)
    
    def get_all_users(self) -> list:
        """Get all users (Supervisor and Admin only)"""
        if not self.require_role("Supervisor"):
            return []
            
        return self.login_manager.get_all_users()
    
    def check_session_validity(self) -> bool:
        """Check if current session is still valid"""
        session = self.session_manager.get_current_session()
        
        if not session:
            return False
            
        if not self.session_manager.is_session_valid(session):
            self.session_ended.emit("Session expired")
            return False
            
        return True
    
    def authenticate_user(self, username: str, pin: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return user info (for testing compatibility)"""
        try:
            user_info = self.login_manager.authenticate_user(username, pin)
            return user_info
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
    
    def login_user(self, username: str, pin: str) -> Optional[UserSession]:
        """Login user and return session (for testing compatibility)"""
        try:
            user_info = self.login_manager.authenticate_user(username, pin)
            
            if user_info:
                session = self.session_manager.create_session(user_info)
                self.session_started.emit(user_info)
                return session
                
            return None
            
        except Exception as e:
            print(f"Login error: {e}")
            return None
    
    def logout_current_user(self):
        """Logout current user (for testing compatibility)"""
        self.logout()
    
    def is_user_logged_in(self) -> bool:
        """Check if user is logged in (for testing compatibility)"""
        return self.is_authenticated()

# Global authentication service instance
_auth_service = None

def get_auth_service() -> AuthenticationService:
    """Get the global authentication service instance"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthenticationService()
    return _auth_service

def require_auth(func):
    """Decorator to require authentication"""
    def wrapper(*args, **kwargs):
        auth = get_auth_service()
        if not auth.is_authenticated():
            auth.permission_denied.emit("Authentication required")
            return None
        return func(*args, **kwargs)
    return wrapper

def require_permission(permission: Permission):
    """Decorator to require specific permission"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            auth = get_auth_service()
            if not auth.require_permission(permission):
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(min_role: str):
    """Decorator to require minimum role"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            auth = get_auth_service()
            if not auth.require_role(min_role):
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator
