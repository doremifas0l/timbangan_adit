#!/usr/bin/env python3
"""
SCALE System Master Data Management Dialog
Provides CRUD operations for Products, Customers/Suppliers, and Transporters
"""

import sys
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QLineEdit, QComboBox, QTextEdit, QCheckBox, QHeaderView,
    QMessageBox, QFormLayout, QGroupBox, QAbstractItemView,
    QFrame, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon

sys.path.append('..')
from database.data_access import DataAccessLayer
from core.config import DATABASE_PATH

class ProductEditDialog(QDialog):
    """Dialog for creating/editing products"""
    
    def __init__(self, parent=None, product_data=None):
        super().__init__(parent)
        self.product_data = product_data
        self.setup_ui()
        
        if product_data:
            self.load_product_data()
    
    def setup_ui(self):
        """Setup the product edit dialog UI"""
        self.setWindowTitle("Product Management" if not self.product_data else "Edit Product")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QFormLayout()
        
        # Product Code
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Auto-generated if empty")
        form_layout.addRow("Product Code:", self.code_edit)
        
        # Product Name (required)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Product name (required)")
        form_layout.addRow("Product Name*:", self.name_edit)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Optional description")
        form_layout.addRow("Description:", self.description_edit)
        
        # Unit
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["KG", "TON", "LB", "G"])
        form_layout.addRow("Unit:", self.unit_combo)
        
        # Active status
        self.active_check = QCheckBox("Active")
        self.active_check.setChecked(True)
        form_layout.addRow("", self.active_check)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_product_data(self):
        """Load existing product data into form"""
        if self.product_data:
            self.code_edit.setText(self.product_data.get('code', ''))
            self.name_edit.setText(self.product_data.get('name', ''))
            self.description_edit.setPlainText(self.product_data.get('description', ''))
            
            unit = self.product_data.get('unit', 'KG')
            index = self.unit_combo.findText(unit)
            if index >= 0:
                self.unit_combo.setCurrentIndex(index)
            
            self.active_check.setChecked(bool(self.product_data.get('is_active', True)))
    
    def get_product_data(self) -> Dict[str, Any]:
        """Get product data from form"""
        return {
            'code': self.code_edit.text().strip() or None,
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip() or None,
            'unit': self.unit_combo.currentText(),
            'is_active': self.active_check.isChecked()
        }
    
    def accept(self):
        """Validate and accept form"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Product name is required.")
            self.name_edit.setFocus()
            return
        
        super().accept()

class PartyEditDialog(QDialog):
    """Dialog for creating/editing parties (customers/suppliers)"""
    
    def __init__(self, parent=None, party_data=None):
        super().__init__(parent)
        self.party_data = party_data
        self.setup_ui()
        
        if party_data:
            self.load_party_data()
    
    def setup_ui(self):
        """Setup the party edit dialog UI"""
        self.setWindowTitle("Customer/Supplier Management" if not self.party_data else "Edit Customer/Supplier")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QFormLayout()
        
        # Party Code
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Auto-generated if empty")
        form_layout.addRow("Code:", self.code_edit)
        
        # Party Name (required)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Customer/Supplier name (required)")
        form_layout.addRow("Name*:", self.name_edit)
        
        # Type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Customer", "Supplier", "Both"])
        form_layout.addRow("Type:", self.type_combo)
        
        # Address
        self.address_edit = QTextEdit()
        self.address_edit.setMaximumHeight(60)
        self.address_edit.setPlaceholderText("Street address")
        form_layout.addRow("Address:", self.address_edit)
        
        # Phone
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("Phone number")
        form_layout.addRow("Phone:", self.phone_edit)
        
        # Email
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Email address")
        form_layout.addRow("Email:", self.email_edit)
        
        # Active status
        self.active_check = QCheckBox("Active")
        self.active_check.setChecked(True)
        form_layout.addRow("", self.active_check)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_party_data(self):
        """Load existing party data into form"""
        if self.party_data:
            self.code_edit.setText(self.party_data.get('code', ''))
            self.name_edit.setText(self.party_data.get('name', ''))
            
            party_type = self.party_data.get('type', 'Customer')
            index = self.type_combo.findText(party_type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
            
            self.address_edit.setPlainText(self.party_data.get('address', ''))
            self.phone_edit.setText(self.party_data.get('phone', ''))
            self.email_edit.setText(self.party_data.get('email', ''))
            
            self.active_check.setChecked(bool(self.party_data.get('is_active', True)))
    
    def get_party_data(self) -> Dict[str, Any]:
        """Get party data from form"""
        return {
            'code': self.code_edit.text().strip() or None,
            'name': self.name_edit.text().strip(),
            'type': self.type_combo.currentText(),
            'address': self.address_edit.toPlainText().strip() or None,
            'phone': self.phone_edit.text().strip() or None,
            'email': self.email_edit.text().strip() or None,
            'is_active': self.active_check.isChecked()
        }
    
    def accept(self):
        """Validate and accept form"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required.")
            self.name_edit.setFocus()
            return
        
        super().accept()

class TransporterEditDialog(QDialog):
    """Dialog for creating/editing transporters"""
    
    def __init__(self, parent=None, transporter_data=None):
        super().__init__(parent)
        self.transporter_data = transporter_data
        self.setup_ui()
        
        if transporter_data:
            self.load_transporter_data()
    
    def setup_ui(self):
        """Setup the transporter edit dialog UI"""
        self.setWindowTitle("Transporter Management" if not self.transporter_data else "Edit Transporter")
        self.setFixedSize(450, 250)
        
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QFormLayout()
        
        # Transporter Code
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Auto-generated if empty")
        form_layout.addRow("Transporter Code:", self.code_edit)
        
        # Transporter Name (required)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Transporter name (required)")
        form_layout.addRow("Transporter Name*:", self.name_edit)
        
        # License Number
        self.license_edit = QLineEdit()
        self.license_edit.setPlaceholderText("Business license number")
        form_layout.addRow("License No:", self.license_edit)
        
        # Phone
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("Phone number")
        form_layout.addRow("Phone:", self.phone_edit)
        
        # Active status
        self.active_check = QCheckBox("Active")
        self.active_check.setChecked(True)
        form_layout.addRow("", self.active_check)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_transporter_data(self):
        """Load existing transporter data into form"""
        if self.transporter_data:
            self.code_edit.setText(self.transporter_data.get('code', ''))
            self.name_edit.setText(self.transporter_data.get('name', ''))
            self.license_edit.setText(self.transporter_data.get('license_no', ''))
            self.phone_edit.setText(self.transporter_data.get('phone', ''))
            
            self.active_check.setChecked(bool(self.transporter_data.get('is_active', True)))
    
    def get_transporter_data(self) -> Dict[str, Any]:
        """Get transporter data from form"""
        return {
            'code': self.code_edit.text().strip() or None,
            'name': self.name_edit.text().strip(),
            'license_no': self.license_edit.text().strip() or None,
            'phone': self.phone_edit.text().strip() or None,
            'is_active': self.active_check.isChecked()
        }
    
    def accept(self):
        """Validate and accept form"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Transporter name is required.")
            self.name_edit.setFocus()
            return
        
        super().accept()

class MasterDataDialog(QDialog):
    """Main master data management dialog with tabbed interface"""
    
    data_changed = pyqtSignal()  # Signal emitted when data is modified
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_access = DataAccessLayer(str(DATABASE_PATH))
        self.setup_ui()
        self.load_all_data()
    
    def setup_ui(self):
        """Setup the main dialog UI"""
        self.setWindowTitle("Master Data Management")
        self.setMinimumSize(800, 600)
        
        # Apply styling
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e1e1e1;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
                color: white;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton.danger {
                background-color: #d83b01;
            }
            QPushButton.danger:hover {
                background-color: #c33400;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Products tab
        self.products_tab = self.create_products_tab()
        self.tab_widget.addTab(self.products_tab, "📦 Products")
        
        # Customers/Suppliers tab
        self.parties_tab = self.create_parties_tab()
        self.tab_widget.addTab(self.parties_tab, "👥 Customers/Suppliers")
        
        # Transporters tab
        self.transporters_tab = self.create_transporters_tab()
        self.tab_widget.addTab(self.transporters_tab, "🚛 Transporters")
        
        layout.addWidget(self.tab_widget)
        
        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        close_layout.addWidget(self.close_btn)
        
        layout.addLayout(close_layout)
        
        self.setLayout(layout)
    
    def create_products_tab(self) -> QWidget:
        """Create the products management tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.add_product_btn = QPushButton("➕ Add Product")
        self.add_product_btn.clicked.connect(self.add_product)
        
        self.edit_product_btn = QPushButton("✏️ Edit Product")
        self.edit_product_btn.clicked.connect(self.edit_product)
        self.edit_product_btn.setEnabled(False)
        
        self.delete_product_btn = QPushButton("🗑️ Delete Product")
        self.delete_product_btn.setProperty("class", "danger")
        self.delete_product_btn.clicked.connect(self.delete_product)
        self.delete_product_btn.setEnabled(False)
        
        self.refresh_products_btn = QPushButton("🔄 Refresh")
        self.refresh_products_btn.clicked.connect(self.load_products_data)
        
        toolbar_layout.addWidget(self.add_product_btn)
        toolbar_layout.addWidget(self.edit_product_btn)
        toolbar_layout.addWidget(self.delete_product_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.refresh_products_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Products table
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels(["Code", "Name", "Description", "Unit", "Status"])
        
        header = self.products_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name column stretches
        
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.products_table.setAlternatingRowColors(True)
        self.products_table.itemSelectionChanged.connect(self.on_product_selection_changed)
        self.products_table.itemDoubleClicked.connect(self.edit_product)
        
        layout.addWidget(self.products_table)
        
        tab.setLayout(layout)
        return tab
    
    def create_parties_tab(self) -> QWidget:
        """Create the parties (customers/suppliers) management tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.add_party_btn = QPushButton("➕ Add Customer/Supplier")
        self.add_party_btn.clicked.connect(self.add_party)
        
        self.edit_party_btn = QPushButton("✏️ Edit")
        self.edit_party_btn.clicked.connect(self.edit_party)
        self.edit_party_btn.setEnabled(False)
        
        self.delete_party_btn = QPushButton("🗑️ Delete")
        self.delete_party_btn.setProperty("class", "danger")
        self.delete_party_btn.clicked.connect(self.delete_party)
        self.delete_party_btn.setEnabled(False)
        
        self.refresh_parties_btn = QPushButton("🔄 Refresh")
        self.refresh_parties_btn.clicked.connect(self.load_parties_data)
        
        toolbar_layout.addWidget(self.add_party_btn)
        toolbar_layout.addWidget(self.edit_party_btn)
        toolbar_layout.addWidget(self.delete_party_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.refresh_parties_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Parties table
        self.parties_table = QTableWidget()
        self.parties_table.setColumnCount(6)
        self.parties_table.setHorizontalHeaderLabels(["Code", "Name", "Type", "Phone", "Email", "Status"])
        
        header = self.parties_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name column stretches
        
        self.parties_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.parties_table.setAlternatingRowColors(True)
        self.parties_table.itemSelectionChanged.connect(self.on_party_selection_changed)
        self.parties_table.itemDoubleClicked.connect(self.edit_party)
        
        layout.addWidget(self.parties_table)
        
        tab.setLayout(layout)
        return tab
    
    def create_transporters_tab(self) -> QWidget:
        """Create the transporters management tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.add_transporter_btn = QPushButton("➕ Add Transporter")
        self.add_transporter_btn.clicked.connect(self.add_transporter)
        
        self.edit_transporter_btn = QPushButton("✏️ Edit")
        self.edit_transporter_btn.clicked.connect(self.edit_transporter)
        self.edit_transporter_btn.setEnabled(False)
        
        self.delete_transporter_btn = QPushButton("🗑️ Delete")
        self.delete_transporter_btn.setProperty("class", "danger")
        self.delete_transporter_btn.clicked.connect(self.delete_transporter)
        self.delete_transporter_btn.setEnabled(False)
        
        self.refresh_transporters_btn = QPushButton("🔄 Refresh")
        self.refresh_transporters_btn.clicked.connect(self.load_transporters_data)
        
        toolbar_layout.addWidget(self.add_transporter_btn)
        toolbar_layout.addWidget(self.edit_transporter_btn)
        toolbar_layout.addWidget(self.delete_transporter_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.refresh_transporters_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Transporters table
        self.transporters_table = QTableWidget()
        self.transporters_table.setColumnCount(5)
        self.transporters_table.setHorizontalHeaderLabels(["Code", "Name", "License No", "Phone", "Status"])
        
        header = self.transporters_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name column stretches
        
        self.transporters_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.transporters_table.setAlternatingRowColors(True)
        self.transporters_table.itemSelectionChanged.connect(self.on_transporter_selection_changed)
        self.transporters_table.itemDoubleClicked.connect(self.edit_transporter)
        
        layout.addWidget(self.transporters_table)
        
        tab.setLayout(layout)
        return tab
    
    def load_all_data(self):
        """Load all master data"""
        self.load_products_data()
        self.load_parties_data()
        self.load_transporters_data()
    
    def load_products_data(self):
        """Load products data into table"""
        try:
            with self.db_access.get_connection() as conn:
                results = conn.execute("""
                    SELECT id, code, name, description, unit, is_active, created_at_utc
                    FROM products 
                    ORDER BY name
                """).fetchall()
                
                self.products_table.setRowCount(len(results))
                
                for row, product in enumerate(results):
                    self.products_table.setItem(row, 0, QTableWidgetItem(product['code'] or ''))
                    self.products_table.setItem(row, 1, QTableWidgetItem(product['name'] or ''))
                    self.products_table.setItem(row, 2, QTableWidgetItem(product['description'] or ''))
                    self.products_table.setItem(row, 3, QTableWidgetItem(product['unit'] or 'KG'))
                    
                    status = "Active" if product['is_active'] else "Inactive"
                    status_item = QTableWidgetItem(status)
                    if not product['is_active']:
                        status_item.setForeground(Qt.GlobalColor.red)
                    self.products_table.setItem(row, 4, status_item)
                    
                    # Store the product ID in the first column for reference
                    self.products_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, product['id'])
                    
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load products: {str(e)}")
    
    def load_parties_data(self):
        """Load parties data into table"""
        try:
            with self.db_access.get_connection() as conn:
                results = conn.execute("""
                    SELECT id, code, name, type, address, phone, email, is_active, created_at_utc
                    FROM parties 
                    ORDER BY name
                """).fetchall()
                
                self.parties_table.setRowCount(len(results))
                
                for row, party in enumerate(results):
                    self.parties_table.setItem(row, 0, QTableWidgetItem(party['code'] or ''))
                    self.parties_table.setItem(row, 1, QTableWidgetItem(party['name'] or ''))
                    self.parties_table.setItem(row, 2, QTableWidgetItem(party['type'] or ''))
                    self.parties_table.setItem(row, 3, QTableWidgetItem(party['phone'] or ''))
                    self.parties_table.setItem(row, 4, QTableWidgetItem(party['email'] or ''))
                    
                    status = "Active" if party['is_active'] else "Inactive"
                    status_item = QTableWidgetItem(status)
                    if not party['is_active']:
                        status_item.setForeground(Qt.GlobalColor.red)
                    self.parties_table.setItem(row, 5, status_item)
                    
                    # Store the party ID in the first column for reference
                    self.parties_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, party['id'])
                    
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load customers/suppliers: {str(e)}")
    
    def load_transporters_data(self):
        """Load transporters data into table"""
        try:
            with self.db_access.get_connection() as conn:
                results = conn.execute("""
                    SELECT id, code, name, license_no, phone, is_active, created_at_utc
                    FROM transporters 
                    ORDER BY name
                """).fetchall()
                
                self.transporters_table.setRowCount(len(results))
                
                for row, transporter in enumerate(results):
                    self.transporters_table.setItem(row, 0, QTableWidgetItem(transporter['code'] or ''))
                    self.transporters_table.setItem(row, 1, QTableWidgetItem(transporter['name'] or ''))
                    self.transporters_table.setItem(row, 2, QTableWidgetItem(transporter['license_no'] or ''))
                    self.transporters_table.setItem(row, 3, QTableWidgetItem(transporter['phone'] or ''))
                    
                    status = "Active" if transporter['is_active'] else "Inactive"
                    status_item = QTableWidgetItem(status)
                    if not transporter['is_active']:
                        status_item.setForeground(Qt.GlobalColor.red)
                    self.transporters_table.setItem(row, 4, status_item)
                    
                    # Store the transporter ID in the first column for reference
                    self.transporters_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, transporter['id'])
                    
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load transporters: {str(e)}")
    
    # Event handlers for selection changes
    def on_product_selection_changed(self):
        """Handle product selection change"""
        has_selection = bool(self.products_table.currentRow() >= 0)
        self.edit_product_btn.setEnabled(has_selection)
        self.delete_product_btn.setEnabled(has_selection)
    
    def on_party_selection_changed(self):
        """Handle party selection change"""
        has_selection = bool(self.parties_table.currentRow() >= 0)
        self.edit_party_btn.setEnabled(has_selection)
        self.delete_party_btn.setEnabled(has_selection)
    
    def on_transporter_selection_changed(self):
        """Handle transporter selection change"""
        has_selection = bool(self.transporters_table.currentRow() >= 0)
        self.edit_transporter_btn.setEnabled(has_selection)
        self.delete_transporter_btn.setEnabled(has_selection)
    
    # Product CRUD operations
    def add_product(self):
        """Add a new product"""
        dialog = ProductEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                data = dialog.get_product_data()
                self.save_product(data)
                self.load_products_data()
                self.data_changed.emit()
                QMessageBox.information(self, "Success", "Product created successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create product: {str(e)}")
    
    def edit_product(self):
        """Edit selected product"""
        current_row = self.products_table.currentRow()
        if current_row < 0:
            return
        
        # Get product data
        product_id = self.products_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        
        try:
            with self.db_access.get_connection() as conn:
                product = conn.execute(
                    "SELECT * FROM products WHERE id = ?", (product_id,)
                ).fetchone()
                
                if product:
                    product_dict = dict(product)
                    dialog = ProductEditDialog(self, product_dict)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        data = dialog.get_product_data()
                        self.save_product(data, product_id)
                        self.load_products_data()
                        self.data_changed.emit()
                        QMessageBox.information(self, "Success", "Product updated successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit product: {str(e)}")
    
    def delete_product(self):
        """Delete selected product"""
        current_row = self.products_table.currentRow()
        if current_row < 0:
            return
        
        product_name = self.products_table.item(current_row, 1).text()
        product_id = self.products_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the product '{product_name}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with self.db_access.get_connection() as conn:
                    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
                    conn.commit()
                    
                self.load_products_data()
                self.data_changed.emit()
                QMessageBox.information(self, "Success", "Product deleted successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete product: {str(e)}")
    
    def save_product(self, data: Dict[str, Any], product_id: Optional[str] = None):
        """Save product data to database"""
        with self.db_access.get_connection() as conn:
            current_time = datetime.utcnow().isoformat()
            
            if product_id:  # Update existing
                conn.execute("""
                    UPDATE products 
                    SET code = ?, name = ?, description = ?, unit = ?, is_active = ?
                    WHERE id = ?
                """, (
                    data['code'], data['name'], data['description'], 
                    data['unit'], data['is_active'], product_id
                ))
            else:  # Create new
                new_id = str(uuid.uuid4())
                # Auto-generate code if not provided
                code = data['code']
                if not code:
                    # Generate code based on name (first 3 chars + random)
                    name_part = ''.join(c.upper() for c in data['name'][:3] if c.isalnum())
                    code = f"{name_part}{str(uuid.uuid4())[:4].upper()}"
                
                conn.execute("""
                    INSERT INTO products (id, code, name, description, unit, is_active, created_at_utc)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_id, code, data['name'], data['description'],
                    data['unit'], data['is_active'], current_time
                ))
            
            conn.commit()
    
    # Party CRUD operations
    def add_party(self):
        """Add a new party"""
        dialog = PartyEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                data = dialog.get_party_data()
                self.save_party(data)
                self.load_parties_data()
                self.data_changed.emit()
                QMessageBox.information(self, "Success", "Customer/Supplier created successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create customer/supplier: {str(e)}")
    
    def edit_party(self):
        """Edit selected party"""
        current_row = self.parties_table.currentRow()
        if current_row < 0:
            return
        
        # Get party data
        party_id = self.parties_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        
        try:
            with self.db_access.get_connection() as conn:
                party = conn.execute(
                    "SELECT * FROM parties WHERE id = ?", (party_id,)
                ).fetchone()
                
                if party:
                    party_dict = dict(party)
                    dialog = PartyEditDialog(self, party_dict)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        data = dialog.get_party_data()
                        self.save_party(data, party_id)
                        self.load_parties_data()
                        self.data_changed.emit()
                        QMessageBox.information(self, "Success", "Customer/Supplier updated successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit customer/supplier: {str(e)}")
    
    def delete_party(self):
        """Delete selected party"""
        current_row = self.parties_table.currentRow()
        if current_row < 0:
            return
        
        party_name = self.parties_table.item(current_row, 1).text()
        party_id = self.parties_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{party_name}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with self.db_access.get_connection() as conn:
                    conn.execute("DELETE FROM parties WHERE id = ?", (party_id,))
                    conn.commit()
                    
                self.load_parties_data()
                self.data_changed.emit()
                QMessageBox.information(self, "Success", "Customer/Supplier deleted successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete customer/supplier: {str(e)}")
    
    def save_party(self, data: Dict[str, Any], party_id: Optional[str] = None):
        """Save party data to database"""
        with self.db_access.get_connection() as conn:
            current_time = datetime.utcnow().isoformat()
            
            if party_id:  # Update existing
                conn.execute("""
                    UPDATE parties 
                    SET code = ?, name = ?, type = ?, address = ?, phone = ?, email = ?, is_active = ?
                    WHERE id = ?
                """, (
                    data['code'], data['name'], data['type'], data['address'],
                    data['phone'], data['email'], data['is_active'], party_id
                ))
            else:  # Create new
                new_id = str(uuid.uuid4())
                # Auto-generate code if not provided
                code = data['code']
                if not code:
                    # Generate code based on name and type
                    name_part = ''.join(c.upper() for c in data['name'][:3] if c.isalnum())
                    type_part = data['type'][0].upper()  # C, S, or B
                    code = f"{type_part}{name_part}{str(uuid.uuid4())[:3].upper()}"
                
                conn.execute("""
                    INSERT INTO parties (id, code, name, type, address, phone, email, is_active, created_at_utc)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_id, code, data['name'], data['type'], data['address'],
                    data['phone'], data['email'], data['is_active'], current_time
                ))
            
            conn.commit()
    
    # Transporter CRUD operations
    def add_transporter(self):
        """Add a new transporter"""
        dialog = TransporterEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                data = dialog.get_transporter_data()
                self.save_transporter(data)
                self.load_transporters_data()
                self.data_changed.emit()
                QMessageBox.information(self, "Success", "Transporter created successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create transporter: {str(e)}")
    
    def edit_transporter(self):
        """Edit selected transporter"""
        current_row = self.transporters_table.currentRow()
        if current_row < 0:
            return
        
        # Get transporter data
        transporter_id = self.transporters_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        
        try:
            with self.db_access.get_connection() as conn:
                transporter = conn.execute(
                    "SELECT * FROM transporters WHERE id = ?", (transporter_id,)
                ).fetchone()
                
                if transporter:
                    transporter_dict = dict(transporter)
                    dialog = TransporterEditDialog(self, transporter_dict)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        data = dialog.get_transporter_data()
                        self.save_transporter(data, transporter_id)
                        self.load_transporters_data()
                        self.data_changed.emit()
                        QMessageBox.information(self, "Success", "Transporter updated successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit transporter: {str(e)}")
    
    def delete_transporter(self):
        """Delete selected transporter"""
        current_row = self.transporters_table.currentRow()
        if current_row < 0:
            return
        
        transporter_name = self.transporters_table.item(current_row, 1).text()
        transporter_id = self.transporters_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the transporter '{transporter_name}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with self.db_access.get_connection() as conn:
                    conn.execute("DELETE FROM transporters WHERE id = ?", (transporter_id,))
                    conn.commit()
                    
                self.load_transporters_data()
                self.data_changed.emit()
                QMessageBox.information(self, "Success", "Transporter deleted successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete transporter: {str(e)}")
    
    def save_transporter(self, data: Dict[str, Any], transporter_id: Optional[str] = None):
        """Save transporter data to database"""
        with self.db_access.get_connection() as conn:
            current_time = datetime.utcnow().isoformat()
            
            if transporter_id:  # Update existing
                conn.execute("""
                    UPDATE transporters 
                    SET code = ?, name = ?, license_no = ?, phone = ?, is_active = ?
                    WHERE id = ?
                """, (
                    data['code'], data['name'], data['license_no'],
                    data['phone'], data['is_active'], transporter_id
                ))
            else:  # Create new
                new_id = str(uuid.uuid4())
                # Auto-generate code if not provided
                code = data['code']
                if not code:
                    # Generate code based on name
                    name_part = ''.join(c.upper() for c in data['name'][:3] if c.isalnum())
                    code = f"T{name_part}{str(uuid.uuid4())[:3].upper()}"
                
                conn.execute("""
                    INSERT INTO transporters (id, code, name, license_no, phone, is_active, created_at_utc)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_id, code, data['name'], data['license_no'],
                    data['phone'], data['is_active'], current_time
                ))
            
            conn.commit()
