# Login dialog UI component
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QFrame, QApplication, QSpacerItem,
    QSizePolicy, QGridLayout, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QIcon
from datetime import datetime
from typing import Optional, Dict, Any

from auth.login_manager import LoginManager
from auth.session_manager import SessionManager
from database.data_access import DataAccessLayer

class LoginDialog(QDialog):
    """Login dialog for user authentication"""
    
    login_successful = pyqtSignal(dict)  # Emitted when login succeeds
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = None
        self.login_manager = None
        self.session_manager = SessionManager()
        self.login_attempts = 0
        self.max_attempts = 3
        
        self.init_ui()
        self.init_database()
        
    def init_database(self):
        """Initialize database connection"""
        try:
            self.db_manager = DataAccessLayer("scale_system/data/scale_system.db")
            self.login_manager = LoginManager(self.db_manager)
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Database Error", 
                f"Failed to initialize database: {str(e)}\n\nPlease check database connection."
            )
            self.reject()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("SCALE System - Login")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        # Set window flags to prevent closing
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.CustomizeWindowHint
        )
        
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 30, 40, 30)
        
        # Header section
        self.create_header(layout)
        
        # Login form
        self.create_form(layout)
        
        # Buttons
        self.create_buttons(layout)
        
        # Status bar
        self.create_status_bar(layout)
        
        self.setLayout(layout)
        
        # Set focus to username field
        self.username_edit.setFocus()
        
    def create_header(self, layout: QVBoxLayout):
        """Create header section with logo and title"""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.Box)
        header_layout = QVBoxLayout(header_frame)
        
        # Title
        title_label = QLabel("SCALE System")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Subtitle
        subtitle_label = QLabel("Weighbridge Management System v2.0")
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #666666;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        
        layout.addWidget(header_frame)
        
    def create_form(self, layout: QVBoxLayout):
        """Create login form"""
        form_frame = QFrame()
        form_layout = QGridLayout(form_frame)
        form_layout.setSpacing(10)
        
        # Username field
        username_label = QLabel("Username:")
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter your username")
        self.username_edit.returnPressed.connect(self.on_username_enter)
        
        # PIN field
        pin_label = QLabel("PIN:")
        self.pin_edit = QLineEdit()
        self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_edit.setPlaceholderText("Enter your PIN")
        self.pin_edit.returnPressed.connect(self.attempt_login)
        
        # Show PIN checkbox
        self.show_pin_checkbox = QCheckBox("Show PIN")
        self.show_pin_checkbox.stateChanged.connect(self.toggle_pin_visibility)
        
        # Add to form
        form_layout.addWidget(username_label, 0, 0)
        form_layout.addWidget(self.username_edit, 0, 1)
        form_layout.addWidget(pin_label, 1, 0)
        form_layout.addWidget(self.pin_edit, 1, 1)
        form_layout.addWidget(self.show_pin_checkbox, 2, 1)
        
        layout.addWidget(form_frame)
        
    def create_buttons(self, layout: QVBoxLayout):
        """Create login buttons"""
        button_layout = QHBoxLayout()
        
        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.attempt_login)
        self.login_button.setDefault(True)
        
        # Exit button
        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.confirm_exit)
        
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.exit_button)
        
        layout.addLayout(button_layout)
        
    def create_status_bar(self, layout: QVBoxLayout):
        """Create status bar"""
        self.status_label = QLabel("Please enter your credentials")
        self.status_label.setStyleSheet(
            "QLabel { color: #666666; font-size: 9pt; }"
        )
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.status_label)
        
    def on_username_enter(self):
        """Handle Enter key in username field"""
        self.pin_edit.setFocus()
        
    def toggle_pin_visibility(self, checked: int):
        """Toggle PIN field visibility"""
        if checked == 2:  # Qt.CheckState.Checked
            self.pin_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)
            
    def attempt_login(self):
        """Attempt to log in with provided credentials"""
        username = self.username_edit.text().strip()
        pin = self.pin_edit.text().strip()
        
        # Basic validation
        if not username:
            self.show_error("Please enter your username")
            self.username_edit.setFocus()
            return
            
        if not pin:
            self.show_error("Please enter your PIN")
            self.pin_edit.setFocus()
            return
            
        # Disable login button during authentication
        self.login_button.setEnabled(False)
        self.status_label.setText("Authenticating...")
        QApplication.processEvents()
        
        try:
            # Attempt authentication
            user_info = self.login_manager.authenticate_user(username, pin)
            
            if user_info:
                # Authentication successful
                session = self.session_manager.create_session(user_info)
                self.show_success(f"Welcome, {user_info['username']}!")
                
                # Emit success signal with user info
                self.login_successful.emit(user_info)
                
                # Close dialog after short delay
                QTimer.singleShot(1000, self.accept)
                
            else:
                # Authentication failed
                self.login_attempts += 1
                remaining = self.max_attempts - self.login_attempts
                
                if remaining > 0:
                    self.show_error(
                        f"Invalid credentials. {remaining} attempts remaining."
                    )
                    self.clear_form()
                else:
                    self.show_error("Too many failed attempts. Application will exit.")
                    QTimer.singleShot(2000, self.reject)
                    
        except Exception as e:
            self.show_error(f"Login error: {str(e)}")
            
        finally:
            self.login_button.setEnabled(True)
            
    def clear_form(self):
        """Clear the login form"""
        self.pin_edit.clear()
        self.username_edit.setFocus()
        
    def show_error(self, message: str):
        """Show error message"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(
            "QLabel { color: #cc0000; font-size: 9pt; font-weight: bold; }"
        )
        
    def show_success(self, message: str):
        """Show success message"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(
            "QLabel { color: #008000; font-size: 9pt; font-weight: bold; }"
        )
        
    def confirm_exit(self):
        """Confirm application exit"""
        reply = QMessageBox.question(
            self,
            "Exit Application",
            "Are you sure you want to exit the SCALE System?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.reject()
            
    def closeEvent(self, event):
        """Handle dialog close event"""
        # Prevent closing without proper authentication or exit confirmation
        event.ignore()
        self.confirm_exit()
        
    def get_session_manager(self) -> SessionManager:
        """Get the session manager for the main application"""
        return self.session_manager

# Utility function to show login dialog
def show_login_dialog(parent=None) -> Optional[Dict[str, Any]]:
    """Show login dialog and return user info if successful"""
    dialog = LoginDialog(parent)
    
    user_info = None
    
    def on_login_success(info):
        nonlocal user_info
        user_info = info
        
    dialog.login_successful.connect(on_login_success)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return user_info, dialog.get_session_manager()
    
    return None, None

if __name__ == "__main__":
    # Test the login dialog
    app = QApplication(sys.argv)
    
    user_info, session_manager = show_login_dialog()
    
    if user_info:
        print(f"Login successful: {user_info}")
        print(f"Session info: {session_manager.get_session_info()}")
    else:
        print("Login cancelled or failed")
        
    sys.exit()
