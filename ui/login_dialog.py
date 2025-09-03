#!/usr/bin/env python3
"""
SCALE System Enhanced Login Dialog
PIN-based authentication with modern UI design
"""

import sys
import logging
from typing import Dict, Optional
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QGroupBox,
    QMessageBox, QApplication, QFrame, QProgressBar,
    QCheckBox, QWidget, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize,
    pyqtSlot
)
from PyQt6.QtGui import (
    QFont, QIcon, QPalette, QColor, QPixmap,
    QPainter, QBrush, QPen, QIntValidator
)

# Import SCALE system components
sys.path.append('..')
from auth.auth_service import AuthenticationService
from utils.helpers import format_timestamp

class LoginAttemptWorker(QThread):
    """Background thread for login attempts to prevent UI blocking"""
    
    login_completed = pyqtSignal(bool, dict)  # Success, user_data or error_info
    
    def __init__(self, auth_service: AuthenticationService, username: str, pin: str):
        super().__init__()
        self.auth_service = auth_service
        self.username = username
        self.pin = pin
    
    def run(self):
        """Perform login attempt in background"""
        try:
            result = self.auth_service.authenticate_user(self.username, self.pin)
            
            if result['success']:
                self.login_completed.emit(True, result)
            else:
                self.login_completed.emit(False, {'error': result.get('error', 'Authentication failed')})
                
        except Exception as e:
            self.login_completed.emit(False, {'error': str(e)})

class LoginDialog(QDialog):
    """Enhanced login dialog with PIN authentication"""
    
    def __init__(self, auth_service: AuthenticationService, parent=None):
        super().__init__(parent)
        
        self.auth_service = auth_service
        self.authenticated_user = None
        self.login_worker = None
        
        # Login attempt tracking
        self.attempt_count = 0
        self.max_attempts = 3
        self.lockout_timer = None
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup the login dialog UI"""
        
        self.setWindowTitle("SCALE System - Login")
        self.setFixedSize(400, 500)
        self.setModal(True)
        
        # Remove window buttons and make it non-resizable
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.MSWindowsFixedSizeDialogHint |
            Qt.WindowType.WindowTitleHint
        )
        
        # Apply professional styling
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0f0f0, stop:1 #e0e0e0);
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 12px;
                margin-top: 15px;
                padding-top: 20px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f8f8);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 15px 0 15px;
                background-color: #f0f0f0;
                border-radius: 4px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078d4, stop:1 #005a9e);
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #106ebe, stop:1 #0078d4);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #005a9e, stop:1 #004578);
            }
            QPushButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #cccccc, stop:1 #999999);
                color: #666666;
            }
            QPushButton.cancel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #666666, stop:1 #444444);
            }
            QPushButton.cancel:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #777777, stop:1 #555555);
            }
            QLineEdit {
                padding: 12px;
                border: 2px solid #cccccc;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #0078d4;
            }
            QLabel.title {
                color: #2c2c2c;
                font-size: 18px;
                font-weight: bold;
            }
            QLabel.subtitle {
                color: #666666;
                font-size: 12px;
            }
            QLabel.error {
                color: #d83b01;
                font-weight: bold;
                font-size: 12px;
            }
            QLabel.success {
                color: #107c10;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        
        # Header section
        header_frame = QFrame()
        header_layout = QVBoxLayout()
        
        # Logo/Title
        title_label = QLabel("SCALE System")
        title_label.setProperty("class", "title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Professional Weighbridge Management")
        subtitle_label.setProperty("class", "subtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        version_label = QLabel("Version 2.0")
        version_label.setProperty("class", "subtitle")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(version_label)
        
        header_frame.setLayout(header_layout)
        main_layout.addWidget(header_frame)
        
        # Login form
        login_group = QGroupBox("User Authentication")
        login_layout = QVBoxLayout()
        login_layout.setSpacing(15)
        
        # Username field
        username_layout = QVBoxLayout()
        username_layout.setSpacing(5)
        
        username_label = QLabel("Username:")
        username_layout.addWidget(username_label)
        
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter your username")
        self.username_edit.returnPressed.connect(self.focus_pin_field)
        username_layout.addWidget(self.username_edit)
        
        login_layout.addLayout(username_layout)
        
        # PIN field
        pin_layout = QVBoxLayout()
        pin_layout.setSpacing(5)
        
        pin_label = QLabel("PIN:")
        pin_layout.addWidget(pin_label)
        
        self.pin_edit = QLineEdit()
        self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_edit.setPlaceholderText("Enter your PIN")
        self.pin_edit.setValidator(QIntValidator(1000, 999999))  # 4-6 digits
        self.pin_edit.returnPressed.connect(self.attempt_login)
        pin_layout.addWidget(self.pin_edit)
        
        login_layout.addLayout(pin_layout)
        
        # Show PIN checkbox
        self.show_pin_check = QCheckBox("Show PIN")
        self.show_pin_check.stateChanged.connect(self.toggle_pin_visibility)
        login_layout.addWidget(self.show_pin_check)
        
        # Status/Error display
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        login_layout.addWidget(self.status_label)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        login_layout.addWidget(self.progress_bar)
        
        login_group.setLayout(login_layout)
        main_layout.addWidget(login_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.login_btn = QPushButton("🔑 Login")
        self.login_btn.clicked.connect(self.attempt_login)
        self.login_btn.setDefault(True)
        
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.setProperty("class", "cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.login_btn)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
        
        # Footer with default accounts info
        footer_frame = QFrame()
        footer_layout = QVBoxLayout()
        
        info_label = QLabel("Default Test Accounts:")
        info_label.setProperty("class", "subtitle")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(info_label)
        
        accounts_label = QLabel(
            "Admin: admin / 1234\n"
            "Supervisor: supervisor / 2345\n"
            "Operator: operator / 3456"
        )
        accounts_label.setProperty("class", "subtitle")
        accounts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(accounts_label)
        
        footer_frame.setLayout(footer_layout)
        main_layout.addWidget(footer_frame)
        
        self.setLayout(main_layout)
        
        # Set focus to username field
        self.username_edit.setFocus()
    
    def setup_connections(self):
        """Setup signal connections"""
        pass
    
    @pyqtSlot()
    def focus_pin_field(self):
        """Move focus to PIN field when Enter is pressed in username field"""
        self.pin_edit.setFocus()
    
    @pyqtSlot()
    def toggle_pin_visibility(self):
        """Toggle PIN field visibility"""
        if self.show_pin_check.isChecked():
            self.pin_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)
    
    @pyqtSlot()
    def attempt_login(self):
        """Attempt to authenticate user"""
        
        username = self.username_edit.text().strip()
        pin = self.pin_edit.text().strip()
        
        # Validate input
        if not username:
            self.show_error("Please enter your username.")
            self.username_edit.setFocus()
            return
        
        if not pin:
            self.show_error("Please enter your PIN.")
            self.pin_edit.setFocus()
            return
        
        if len(pin) < 4:
            self.show_error("PIN must be at least 4 digits.")
            self.pin_edit.setFocus()
            return
        
        # Check attempt limits
        if self.attempt_count >= self.max_attempts:
            self.show_error("Too many failed attempts. Please wait before trying again.")
            self.start_lockout_timer()
            return
        
        # Disable UI during login attempt
        self.set_ui_enabled(False)
        self.show_progress("Authenticating...")
        
        # Start login attempt in background thread
        self.login_worker = LoginAttemptWorker(self.auth_service, username, pin)
        self.login_worker.login_completed.connect(self.on_login_completed)
        self.login_worker.start()
    
    @pyqtSlot(bool, dict)
    def on_login_completed(self, success: bool, result: Dict):
        """Handle login attempt completion"""
        
        self.set_ui_enabled(True)
        self.hide_progress()
        
        if success:
            self.authenticated_user = result['user']
            self.show_success(f"Welcome, {self.authenticated_user['username']}!")
            
            # Short delay to show success message, then accept dialog
            QTimer.singleShot(1000, self.accept)
            
        else:
            self.attempt_count += 1
            remaining_attempts = self.max_attempts - self.attempt_count
            
            error_msg = result.get('error', 'Authentication failed')
            
            if remaining_attempts > 0:
                self.show_error(f"{error_msg}\nAttempts remaining: {remaining_attempts}")
            else:
                self.show_error("Maximum login attempts exceeded. Access temporarily locked.")
                self.start_lockout_timer()
            
            # Clear PIN field for security
            self.pin_edit.clear()
            self.pin_edit.setFocus()
    
    def show_error(self, message: str):
        """Display error message"""
        self.status_label.setText(f"❌ {message}")
        self.status_label.setProperty("class", "error")
        self.status_label.style().polish(self.status_label)
    
    def show_success(self, message: str):
        """Display success message"""
        self.status_label.setText(f"✅ {message}")
        self.status_label.setProperty("class", "success")
        self.status_label.style().polish(self.status_label)
    
    def show_progress(self, message: str):
        """Show progress indicator"""
        self.status_label.setText(message)
        self.status_label.setProperty("class", "")
        self.status_label.style().polish(self.status_label)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
    
    def hide_progress(self):
        """Hide progress indicator"""
        self.progress_bar.setVisible(False)
    
    def set_ui_enabled(self, enabled: bool):
        """Enable/disable UI elements during login attempt"""
        self.username_edit.setEnabled(enabled)
        self.pin_edit.setEnabled(enabled)
        self.login_btn.setEnabled(enabled)
        self.show_pin_check.setEnabled(enabled)
    
    def start_lockout_timer(self):
        """Start lockout timer after max attempts"""
        lockout_duration = 300000  # 5 minutes in milliseconds
        
        self.set_ui_enabled(False)
        
        self.lockout_timer = QTimer()
        self.lockout_timer.timeout.connect(self.end_lockout)
        self.lockout_timer.start(lockout_duration)
        
        # Show countdown
        self.show_lockout_countdown(lockout_duration)
    
    def show_lockout_countdown(self, duration_ms: int):
        """Show lockout countdown"""
        minutes = duration_ms // 60000
        self.show_error(f"Account locked for {minutes} minutes due to failed login attempts.")
    
    def end_lockout(self):
        """End lockout period"""
        if self.lockout_timer:
            self.lockout_timer.stop()
            self.lockout_timer = None
        
        self.attempt_count = 0
        self.set_ui_enabled(True)
        self.status_label.clear()
        
        # Clear fields and focus username
        self.username_edit.clear()
        self.pin_edit.clear()
        self.username_edit.setFocus()
    
    def get_authenticated_user(self) -> Optional[Dict]:
        """Get the authenticated user data after successful login"""
        return self.authenticated_user
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        # Allow Escape to cancel
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        # Stop any running worker threads
        if self.login_worker and self.login_worker.isRunning():
            self.login_worker.quit()
            self.login_worker.wait()
        
        if self.lockout_timer:
            self.lockout_timer.stop()
        
        event.accept()

# Demo application to test the dialog
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create mock authentication service
    class MockAuthService:
        def authenticate_user(self, username, pin):
            # Mock authentication for testing
            test_users = {
                'admin': {'pin': '1234', 'role': 'Admin'},
                'supervisor': {'pin': '2345', 'role': 'Supervisor'},
                'operator': {'pin': '3456', 'role': 'Operator'}
            }
            
            if username in test_users and test_users[username]['pin'] == pin:
                return {
                    'success': True,
                    'user': {
                        'user_id': 1,
                        'username': username,
                        'role': test_users[username]['role'],
                        'login_time': format_timestamp(datetime.now())
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'Invalid username or PIN'
                }
    
    auth_service = MockAuthService()
    
    dialog = LoginDialog(auth_service)
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        user = dialog.get_authenticated_user()
        if user:
            print(f"Login successful:")
            print(f"  Username: {user['username']}")
            print(f"  Role: {user['role']}")
            print(f"  Login Time: {user['login_time']}")
    else:
        print("Login cancelled or failed")
    
    sys.exit(0)
