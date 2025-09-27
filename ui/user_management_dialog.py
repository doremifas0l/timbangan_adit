#!/usr/bin/env python3
"""
SCALE System User Management Dialog
Dialog for creating and editing user accounts.
"""

import sys
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QCheckBox
)

class UserManagementDialog(QDialog):
    """Dialog for creating or editing a user."""

    def __init__(self, parent=None, user_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.user_data = user_data
        self.setup_ui()

        if self.user_data:
            self.setWindowTitle("Edit User")
            self.load_user_data()
        else:
            self.setWindowTitle("Add New User")

    def setup_ui(self):
        """Set up the UI elements for the dialog."""
        self.setFixedSize(400, 250)

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Username
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter a unique username")
        form_layout.addRow("Username*:", self.username_edit)

        # Role
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Operator", "Supervisor", "Admin"])
        form_layout.addRow("Role*:", self.role_combo)

        # PIN
        self.pin_edit = QLineEdit()
        self.pin_edit.setPlaceholderText("4-6 digit PIN, leave blank to keep unchanged")
        self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("PIN:", self.pin_edit)

        # Active status
        self.active_check = QCheckBox("User is Active")
        self.active_check.setChecked(True)
        form_layout.addRow("Status:", self.active_check)

        layout.addLayout(form_layout)

        # Buttons
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")

        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        button_layout = QVBoxLayout()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_user_data(self):
        """Load existing user data into the form fields."""
        if not self.user_data:
            return

        self.username_edit.setText(self.user_data.get("username", ""))
        self.username_edit.setReadOnly(True) # Prevent username changes

        role = self.user_data.get("role", "Operator")
        index = self.role_combo.findText(role)
        if index >= 0:
            self.role_combo.setCurrentIndex(index)

        self.active_check.setChecked(bool(self.user_data.get("is_active", True)))

    def get_user_data(self) -> Optional[Dict[str, Any]]:
        """Validate and return the user data from the form."""
        username = self.username_edit.text().strip()
        if not username:
            QMessageBox.warning(self, "Input Error", "Username cannot be empty.")
            return None

        pin = self.pin_edit.text().strip()
        if pin and not (4 <= len(pin) <= 6 and pin.isdigit()):
            QMessageBox.warning(self, "Input Error", "PIN must be 4-6 digits.")
            return None

        return {
            "username": username,
            "role": self.role_combo.currentText(),
            "pin": pin or None,  # Return None if empty
            "is_active": self.active_check.isChecked()
        }

    def accept(self):
        """Handle the save action."""
        if self.get_user_data() is not None:
            super().accept()