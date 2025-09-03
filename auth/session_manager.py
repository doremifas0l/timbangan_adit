# Session Manager for handling user sessions and state
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class UserSession:
    """Represents an active user session"""
    user_id: str
    username: str
    role: str
    login_time: datetime
    last_activity: datetime
    session_expires: datetime
    is_active: bool = True

class SessionManager:
    """Manages user sessions and authentication state"""
    
    def __init__(self):
        self._current_session: Optional[UserSession] = None
        self.session_timeout = timedelta(hours=8)
        self.activity_timeout = timedelta(minutes=30)
        
    def create_session(self, user_info: Dict[str, Any]) -> UserSession:
        """Create a new user session"""
        now = datetime.utcnow()
        
        session = UserSession(
            user_id=user_info['id'],
            username=user_info['username'],
            role=user_info['role'],
            login_time=now,
            last_activity=now,
            session_expires=now + self.session_timeout
        )
        
        self._current_session = session
        return session
    
    def get_current_session(self) -> Optional[UserSession]:
        """Get the current active session"""
        if self._current_session and self.is_session_valid(self._current_session):
            return self._current_session
        return None
    
    def is_session_valid(self, session: UserSession) -> bool:
        """Check if a session is still valid"""
        if not session.is_active:
            return False
            
        now = datetime.utcnow()
        
        # Check if session has expired
        if now > session.session_expires:
            self.end_session("Session expired")
            return False
            
        # Check if user has been inactive too long
        if now > (session.last_activity + self.activity_timeout):
            self.end_session("Inactive timeout")
            return False
            
        return True
    
    def update_activity(self):
        """Update last activity timestamp"""
        if self._current_session:
            self._current_session.last_activity = datetime.utcnow()
    
    def extend_session(self, additional_time: timedelta = None):
        """Extend the current session"""
        if self._current_session:
            if additional_time is None:
                additional_time = self.session_timeout
            
            self._current_session.session_expires = datetime.utcnow() + additional_time
    
    def end_session(self, reason: str = "User logout"):
        """End the current session"""
        if self._current_session:
            self._current_session.is_active = False
            print(f"Session ended: {reason}")
            self._current_session = None
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        if not self._current_session:
            return {}
            
        session = self._current_session
        now = datetime.utcnow()
        
        return {
            'username': session.username,
            'role': session.role,
            'login_time': session.login_time.isoformat(),
            'last_activity': session.last_activity.isoformat(),
            'session_expires': session.session_expires.isoformat(),
            'time_remaining': str(session.session_expires - now),
            'is_active': session.is_active
        }
    
    def require_authentication(self) -> bool:
        """Check if authentication is required"""
        session = self.get_current_session()
        return session is None
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current authenticated user info"""
        session = self.get_current_session()
        if session:
            return {
                'id': session.user_id,
                'username': session.username,
                'role': session.role
            }
        return None
    
    def is_role_authorized(self, required_role: str) -> bool:
        """Check if current user has required role or higher"""
        session = self.get_current_session()
        if not session:
            return False
            
        # Role hierarchy: Admin > Supervisor > Operator
        role_hierarchy = {
            'Operator': 1,
            'Supervisor': 2,
            'Admin': 3
        }
        
        current_level = role_hierarchy.get(session.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return current_level >= required_level
    
    def logout(self):
        """Logout current user"""
        self.end_session("User logout")
