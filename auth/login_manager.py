# Login Manager for user authentication
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from database.data_access import DataAccessLayer
from utils.helpers import validate_username, validate_pin, clean_string

class LoginManager:
    """Handles user login, PIN verification, and authentication"""
    
    def __init__(self, db_manager: DataAccessLayer):
        self.db = db_manager
        self.max_login_attempts = 3
        self.lockout_duration = timedelta(minutes=15)
        self.session_timeout = timedelta(hours=8)
        
    def hash_pin(self, pin: str) -> str:
        """Hash a PIN using SHA-256 with salt"""
        # Using the username as salt for now - in production, use random salt
        salt = "scale_system_salt_2025"
        return hashlib.sha256((pin + salt).encode()).hexdigest()
    
    def authenticate_user(self, username: str, pin: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username and PIN
        
        Returns:
            Dict with user info if successful, None if failed
        """
        if not self.validate_credentials(username, pin):
            return None
            
        # Check if user is locked out
        if self.is_user_locked_out(username):
            self.log_failed_attempt(username, "User is locked out")
            return None
            
        # Get user from database
        user = self.get_user_by_username(username)
        if not user:
            self.log_failed_attempt(username, "User not found")
            return None
            
        # Verify PIN
        pin_hash = self.hash_pin(pin)
        if user['pin_hash'] != pin_hash:
            self.log_failed_attempt(username, "Invalid PIN")
            return None
            
        # Authentication successful
        self.log_successful_login(username)
        self.clear_failed_attempts(username)
        
        return {
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'login_time': datetime.utcnow(),
            'session_expires': datetime.utcnow() + self.session_timeout
        }
    
    def validate_credentials(self, username: str, pin: str) -> bool:
        """Validate input credentials"""
        if not username or not pin:
            return False
            
        # Validate username
        if not validate_username(username):
            return False
            
        # Validate PIN (should be 4-8 digits)
        if not validate_pin(pin):
            return False
            
        return True
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user record from database"""
        try:
            query = "SELECT id, username, pin_hash, role FROM users WHERE username = ? AND active = 1"
            result = self.db.execute_query(query, (username,))
            
            if result:
                return {
                    'id': result[0][0],
                    'username': result[0][1],
                    'pin_hash': result[0][2],
                    'role': result[0][3]
                }
            return None
            
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def is_user_locked_out(self, username: str) -> bool:
        """Check if user is currently locked out due to failed attempts"""
        try:
            query = """
                SELECT COUNT(*) FROM audit_log 
                WHERE operator_id = ? 
                AND action = 'FAILED_LOGIN' 
                AND logged_at_utc > ? 
                ORDER BY logged_at_utc DESC
            """
            cutoff_time = datetime.utcnow() - self.lockout_duration
            result = self.db.execute_query(query, (username, cutoff_time.isoformat()))
            
            if result and result[0][0] >= self.max_login_attempts:
                return True
            return False
            
        except Exception as e:
            print(f"Error checking lockout status: {e}")
            return False
    
    def log_failed_attempt(self, username: str, reason: str):
        """Log failed login attempt"""
        try:
            self.db.log_audit_action(
                operator_id=username,
                action='FAILED_LOGIN',
                entity='users',
                entity_id=username,
                reason=reason,
                before_state={},
                after_state={'failed_reason': reason}
            )
        except Exception as e:
            print(f"Error logging failed attempt: {e}")
    
    def log_successful_login(self, username: str):
        """Log successful login"""
        try:
            self.db.log_audit_action(
                operator_id=username,
                action='SUCCESSFUL_LOGIN',
                entity='users',
                entity_id=username,
                reason='User authenticated successfully',
                before_state={},
                after_state={'login_time': datetime.utcnow().isoformat()}
            )
        except Exception as e:
            print(f"Error logging successful login: {e}")
    
    def clear_failed_attempts(self, username: str):
        """Clear failed login attempts after successful login"""
        # In a more sophisticated system, we might update a separate table
        # For now, the audit log serves as our record
        pass
    
    def create_user(self, username: str, pin: str, role: str, created_by: str) -> bool:
        """Create a new user account"""
        try:
            # Validate inputs
            if not self.validate_credentials(username, pin):
                return False
                
            if role not in ['Operator', 'Supervisor', 'Admin']:
                return False
                
            # Check if username already exists
            if self.get_user_by_username(username):
                return False
                
            # Hash PIN
            pin_hash = self.hash_pin(pin)
            
            # Insert user
            query = """
                INSERT INTO users (username, pin_hash, role, active, created_at_utc, created_by)
                VALUES (?, ?, ?, 1, ?, ?)
            """
            
            self.db.execute_insert(query, (
                username, pin_hash, role, 
                datetime.utcnow().isoformat(), created_by
            ))
            
            # Log user creation
            self.db.log_audit_action(
                operator_id=created_by,
                action='CREATE_USER',
                entity='users',
                entity_id=username,
                reason='New user account created',
                before_state={},
                after_state={'username': username, 'role': role}
            )
            
            return True
            
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    def change_user_pin(self, username: str, old_pin: str, new_pin: str, changed_by: str) -> bool:
        """Change user PIN"""
        try:
            # Verify old PIN first
            if not self.authenticate_user(username, old_pin):
                return False
                
            # Validate new PIN
            if not validate_pin(new_pin):
                return False
                
            # Hash new PIN
            new_pin_hash = self.hash_pin(new_pin)
            
            # Update PIN
            query = "UPDATE users SET pin_hash = ?, updated_at_utc = ? WHERE username = ?"
            self.db.execute_insert(query, (
                new_pin_hash, 
                datetime.utcnow().isoformat(),
                username
            ))
            
            # Log PIN change
            self.db.log_audit_action(
                operator_id=changed_by,
                action='CHANGE_PIN',
                entity='users',
                entity_id=username,
                reason='User PIN changed',
                before_state={},
                after_state={'pin_changed': True}
            )
            
            return True
            
        except Exception as e:
            print(f"Error changing PIN: {e}")
            return False
    
    def deactivate_user(self, username: str, deactivated_by: str, reason: str) -> bool:
        """Deactivate a user account"""
        try:
            query = "UPDATE users SET active = 0, updated_at_utc = ? WHERE username = ?"
            self.db.execute_insert(query, (
                datetime.utcnow().isoformat(),
                username
            ))
            
            # Log deactivation
            self.db.log_audit_action(
                operator_id=deactivated_by,
                action='DEACTIVATE_USER',
                entity='users',
                entity_id=username,
                reason=reason,
                before_state={'active': True},
                after_state={'active': False}
            )
            
            return True
            
        except Exception as e:
            print(f"Error deactivating user: {e}")
            return False
    
    def get_all_users(self) -> list:
        """Get all users for management purposes"""
        try:
            query = """
                SELECT id, username, role, active, created_at_utc, created_by
                FROM users 
                ORDER BY created_at_utc DESC
            """
            result = self.db.execute_query(query)
            
            users = []
            for row in result:
                users.append({
                    'id': row[0],
                    'username': row[1],
                    'role': row[2],
                    'active': bool(row[3]),
                    'created_at': row[4],
                    'created_by': row[5]
                })
            
            return users
            
        except Exception as e:
            print(f"Error getting users: {e}")
            return []
