# Role-Based Access Control (RBAC) system
from typing import Dict, List, Set, Any
from functools import wraps
from enum import Enum

class Role(Enum):
    """User roles in the system"""
    OPERATOR = "Operator"
    SUPERVISOR = "Supervisor"
    ADMIN = "Admin"

class Permission(Enum):
    """System permissions"""
    # Weighing Operations
    WEIGH_VEHICLE = "weigh_vehicle"
    VIEW_WEIGHTS = "view_weights"
    CAPTURE_WEIGHT = "capture_weight"
    
    # Transaction Management
    CREATE_TRANSACTION = "create_transaction"
    VIEW_TRANSACTION = "view_transaction"
    VOID_TRANSACTION = "void_transaction"
    MANUAL_OVERRIDE = "manual_override"
    
    # Master Data
    VIEW_MASTER_DATA = "view_master_data"
    CREATE_MASTER_DATA = "create_master_data"
    UPDATE_MASTER_DATA = "update_master_data"
    DELETE_MASTER_DATA = "delete_master_data"
    
    # Reports
    VIEW_BASIC_REPORTS = "view_basic_reports"
    VIEW_EXCEPTION_REPORTS = "view_exception_reports"
    EXPORT_REPORTS = "export_reports"
    
    # User Management
    VIEW_USERS = "view_users"
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DEACTIVATE_USER = "deactivate_user"
    
    # System Settings
    VIEW_SETTINGS = "view_settings"
    UPDATE_SETTINGS = "update_settings"
    BACKUP_RESTORE = "backup_restore"
    
    # Hardware & Calibration
    VIEW_HARDWARE_STATUS = "view_hardware_status"
    CONFIGURE_HARDWARE = "configure_hardware"
    CALIBRATE_SCALE = "calibrate_scale"
    
    # Audit & Logs
    VIEW_AUDIT_LOGS = "view_audit_logs"
    VIEW_SYSTEM_LOGS = "view_system_logs"

class RoleBasedAccessControl:
    """RBAC implementation for the SCALE system"""
    
    def __init__(self):
        self._role_permissions = self._initialize_role_permissions()
        
    def _initialize_role_permissions(self) -> Dict[Role, Set[Permission]]:
        """Initialize role-permission mappings"""
        
        # Start with Operator permissions
        operator_permissions = {
            # Basic weighing operations
            Permission.WEIGH_VEHICLE,
            Permission.VIEW_WEIGHTS,
            Permission.CAPTURE_WEIGHT,
            Permission.CREATE_TRANSACTION,
            Permission.VIEW_TRANSACTION,
            
            # Limited master data access
            Permission.VIEW_MASTER_DATA,
            Permission.CREATE_MASTER_DATA,  # Can add vehicles, products inline
            
            # Basic reports
            Permission.VIEW_BASIC_REPORTS,
            
            # Hardware status
            Permission.VIEW_HARDWARE_STATUS,
        }
        
        # Supervisor permissions include all Operator permissions plus additional ones
        supervisor_permissions = operator_permissions.copy()
        supervisor_permissions.update({
            # Additional transaction management
            Permission.VOID_TRANSACTION,
            Permission.MANUAL_OVERRIDE,
            
            # Full master data management
            Permission.UPDATE_MASTER_DATA,
            Permission.DELETE_MASTER_DATA,
            
            # Advanced reports
            Permission.VIEW_EXCEPTION_REPORTS,
            Permission.EXPORT_REPORTS,
            
            # Limited user management
            Permission.VIEW_USERS,
            
            # Audit logs
            Permission.VIEW_AUDIT_LOGS,
        })
        
        # Admin permissions include all Supervisor permissions plus additional ones
        admin_permissions = supervisor_permissions.copy()
        admin_permissions.update({
            # Full user management
            Permission.CREATE_USER,
            Permission.UPDATE_USER,
            Permission.DEACTIVATE_USER,
            
            # System settings
            Permission.VIEW_SETTINGS,
            Permission.UPDATE_SETTINGS,
            Permission.BACKUP_RESTORE,
            
            # Hardware configuration
            Permission.CONFIGURE_HARDWARE,
            Permission.CALIBRATE_SCALE,
            
            # System logs
            Permission.VIEW_SYSTEM_LOGS,
        })
        
        # Create the final permissions dictionary
        permissions = {
            Role.OPERATOR: operator_permissions,
            Role.SUPERVISOR: supervisor_permissions,
            Role.ADMIN: admin_permissions
        }
        
        return permissions
    
    def has_permission(self, role: str, permission: Permission) -> bool:
        """Check if a role has a specific permission"""
        try:
            role_enum = Role(role)
            return permission in self._role_permissions.get(role_enum, set())
        except ValueError:
            return False
    
    def get_role_permissions(self, role: str) -> List[str]:
        """Get all permissions for a role"""
        try:
            role_enum = Role(role)
            permissions = self._role_permissions.get(role_enum, set())
            return [p.value for p in permissions]
        except ValueError:
            return []
    
    def can_perform_action(self, user_role: str, action: str) -> bool:
        """Check if a user role can perform a specific action"""
        # Map common actions to permissions
        action_permission_map = {
            'weigh_in': Permission.WEIGH_VEHICLE,
            'weigh_out': Permission.WEIGH_VEHICLE,
            'capture_weight': Permission.CAPTURE_WEIGHT,
            'void_transaction': Permission.VOID_TRANSACTION,
            'manual_override': Permission.MANUAL_OVERRIDE,
            'create_vehicle': Permission.CREATE_MASTER_DATA,
            'update_vehicle': Permission.UPDATE_MASTER_DATA,
            'delete_vehicle': Permission.DELETE_MASTER_DATA,
            'view_reports': Permission.VIEW_BASIC_REPORTS,
            'view_exception_reports': Permission.VIEW_EXCEPTION_REPORTS,
            'export_data': Permission.EXPORT_REPORTS,
            'manage_users': Permission.CREATE_USER,
            'configure_system': Permission.UPDATE_SETTINGS,
            'backup_database': Permission.BACKUP_RESTORE,
            'calibrate_hardware': Permission.CALIBRATE_SCALE,
        }
        
        permission = action_permission_map.get(action)
        if permission:
            return self.has_permission(user_role, permission)
        
        return False
    
    def require_permission(self, permission: Permission):
        """Decorator to require a specific permission"""
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                # This would be used with a session manager
                # For now, we'll just return the function
                return func(self, *args, **kwargs)
            return wrapper
        return decorator
    
    def require_role(self, min_role: Role):
        """Decorator to require a minimum role level"""
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                # This would be used with a session manager
                # For now, we'll just return the function
                return func(self, *args, **kwargs)
            return wrapper
        return decorator
    
    def get_accessible_features(self, role: str) -> Dict[str, List[str]]:
        """Get features accessible to a role, organized by category"""
        permissions = self.get_role_permissions(role)
        
        features = {
            'weighing': [],
            'transactions': [],
            'master_data': [],
            'reports': [],
            'users': [],
            'system': [],
            'hardware': []
        }
        
        # Map permissions to feature categories
        permission_features = {
            'weigh_vehicle': ('weighing', 'Vehicle Weighing'),
            'capture_weight': ('weighing', 'Weight Capture'),
            'create_transaction': ('transactions', 'Create Transaction'),
            'void_transaction': ('transactions', 'Void Transaction'),
            'manual_override': ('transactions', 'Manual Override'),
            'view_master_data': ('master_data', 'View Master Data'),
            'create_master_data': ('master_data', 'Create Master Data'),
            'update_master_data': ('master_data', 'Update Master Data'),
            'delete_master_data': ('master_data', 'Delete Master Data'),
            'view_basic_reports': ('reports', 'Basic Reports'),
            'view_exception_reports': ('reports', 'Exception Reports'),
            'export_reports': ('reports', 'Export Reports'),
            'view_users': ('users', 'View Users'),
            'create_user': ('users', 'Create User'),
            'update_user': ('users', 'Update User'),
            'deactivate_user': ('users', 'Deactivate User'),
            'view_settings': ('system', 'View Settings'),
            'update_settings': ('system', 'Update Settings'),
            'backup_restore': ('system', 'Backup & Restore'),
            'configure_hardware': ('hardware', 'Configure Hardware'),
            'calibrate_scale': ('hardware', 'Calibrate Scale'),
        }
        
        for permission in permissions:
            if permission in permission_features:
                category, feature_name = permission_features[permission]
                features[category].append(feature_name)
        
        return features

def require_authentication(func):
    """Decorator to require user authentication"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # In actual implementation, this would check session manager
        # For now, just pass through
        return func(*args, **kwargs)
    return wrapper

def require_permission(permission: Permission):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # In actual implementation, this would check RBAC
            # For now, just pass through
            return func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(min_role: Role):
    """Decorator to require minimum role"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # In actual implementation, this would check role hierarchy
            # For now, just pass through
            return func(*args, **kwargs)
        return wrapper
    return decorator
