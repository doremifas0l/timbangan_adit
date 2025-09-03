# Authentication module for SCALE System
# Handles user authentication, sessions, and security

from .login_manager import LoginManager
from .session_manager import SessionManager, UserSession
from .rbac import RoleBasedAccessControl, Role, Permission
from .auth_service import AuthenticationService, get_auth_service

__all__ = [
    'LoginManager', 'SessionManager', 'UserSession',
    'RoleBasedAccessControl', 'Role', 'Permission',
    'AuthenticationService', 'get_auth_service'
]
