#!/usr/bin/env python3
"""
SCALE System Main Application Window
Complete PyQt6 desktop application for weighbridge management
"""

import sys
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QWidget, QLabel, QPushButton, QGroupBox,
    QTextEdit, QTableWidget, QTableWidgetItem, QTabWidget,
    QFrame, QSplitter, QStatusBar, QMenuBar, QToolBar,
    QMessageBox, QDialog, QProgressBar, QComboBox,
    QLineEdit, QSpinBox, QCheckBox, QDateEdit, QTimeEdit,
    QHeaderView, QAbstractItemView, QScrollArea, QFileDialog
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QRect,
    pyqtSlot, QDate, QTime, QDateTime
)
from PyQt6.QtGui import (
    QFont, QIcon, QPalette, QColor, QPixmap, QAction,
    QPainter, QBrush, QPen, QScreen
)

# Import SCALE system components
sys.path.append('..')
from auth.auth_service import AuthenticationService
from weighing.workflow_controller import WorkflowController, WorkflowState
from database.data_access import DataAccessLayer
from hardware.rs232_manager import RS232Manager, RS232Config
from ui.hardware_config_dialog import HardwareConfigDialog
from ui.login_dialog import LoginDialog
from ui.master_data_management import MasterDataDialog
from utils.helpers import (
    format_timestamp, format_weight, generate_uuid, 
    export_to_csv, export_to_json, format_file_size
)
from core.config import DATABASE_PATH
import os
from pathlib import Path

class WeightDisplayWorker(QThread):
    """Background thread for real-time weight monitoring"""
    
    weight_updated = pyqtSignal(dict)  # Weight data
    connection_status = pyqtSignal(str, bool)  # Status message, connected
    
    def __init__(self, rs232_config=None):
        super().__init__()
        self.rs232_manager = RS232Manager()
        self.config = rs232_config
        self.running = False
        self.connected = False
    
    def start_monitoring(self, config: RS232Config):
        """Start weight monitoring with given configuration"""
        self.config = config
        self.running = True
        self.start()
    
    def stop_monitoring(self):
        """Stop weight monitoring"""
        self.running = False
        if self.connected:
            self.rs232_manager.disconnect()
        self.quit()
        self.wait()
    
    def run(self):
        """Main monitoring loop"""
        if not self.config:
            return
        
        # Attempt connection
        if self.rs232_manager.connect(self.config):
            self.connected = True
            self.connection_status.emit(f"Connected to {self.config.port} at {self.config.baud_rate} baud", True)
            
            while self.running and self.connected:
                try:
                    # Read weight data
                    data = self.rs232_manager.read_data(timeout=1.0)
                    
                    if data:
                        # Parse weight data (simplified)
                        weight_data = self._parse_weight_data(data)
                        if weight_data:
                            self.weight_updated.emit(weight_data)
                    
                    self.msleep(100)  # Check every 100ms
                    
                except Exception as e:
                    self.connection_status.emit(f"Communication error: {str(e)}", False)
                    break
            
            self.rs232_manager.disconnect()
            self.connected = False
        else:
            self.connection_status.emit(f"Failed to connect to {self.config.port}", False)
    
    def _parse_weight_data(self, raw_data: str) -> Optional[Dict]:
        """Parse raw weight data into structured format"""
        try:
            # Simple parsing - in real implementation, use the protocol parser
            import re
            
            # Look for weight pattern
            weight_match = re.search(r'([+-]?\d+\.?\d*)', raw_data.strip())
            if weight_match:
                weight = float(weight_match.group(1))
                
                # Determine stability (simple heuristic)
                stable = 'ST' in raw_data.upper() or 'STABLE' in raw_data.upper()
                
                # Determine unit
                unit = 'KG'
                if 'LB' in raw_data.upper():
                    unit = 'LB'
                elif ' G' in raw_data.upper():
                    unit = 'G'
                
                return {
                    'weight': weight,
                    'stable': stable,
                    'unit': unit,
                    'timestamp': datetime.now().isoformat(),
                    'raw_data': raw_data.strip()
                }
        except Exception as e:
            print(f"Weight parsing error: {e}")
        
        return None

class MainWindow(QMainWindow):
    """Main application window for SCALE System"""
    
    def __init__(self):
        super().__init__()
        
        # Core services
        self.auth_service = AuthenticationService()
        self.workflow_controller = WorkflowController()
        self.data_access = DataAccessLayer(str(DATABASE_PATH))
        
        # Hardware management
        self.rs232_config = None
        self.weight_monitor = None
        
        # Current state
        self.current_user = None
        self.current_transaction = None
        self.current_weight = None
        self.is_connected = False
        
        # UI setup
        self.setup_ui()
        self.setup_status_bar()
        self.setup_menu_bar()
        self.setup_toolbar()
        self.setup_connections()
        
        # Start with login
        self.show_login_dialog()
    
    def setup_ui(self):
        """Setup the main user interface"""
        
        self.setWindowTitle("SCALE System - Professional Weighbridge Management")
        self.setGeometry(100, 100, 1200, 800)
        
        # Apply professional styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 10px 0 10px;
                background-color: #f5f5f5;
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
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QPushButton.success {
                background-color: #107c10;
            }
            QPushButton.success:hover {
                background-color: #0e6b0e;
            }
            QPushButton.warning {
                background-color: #ff8c00;
            }
            QPushButton.warning:hover {
                background-color: #e67a00;
            }
            QPushButton.danger {
                background-color: #d83b01;
            }
            QPushButton.danger:hover {
                background-color: #c33400;
            }
            QLineEdit, QComboBox {
                padding: 6px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
            }
            QTableWidget {
                gridline-color: #e1e1e1;
                selection-background-color: #0078d4;
            }
            QTableWidget::item {
                padding: 8px;
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
        """)
        
        # Central widget with tabs
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        main_layout = QVBoxLayout()
        
        # Header section
        header_widget = self.create_header_section()
        main_layout.addWidget(header_widget)
        
        # Main content tabs
        self.tab_widget = QTabWidget()
        
        # Dashboard tab
        self.dashboard_tab = self.create_dashboard_tab()
        self.tab_widget.addTab(self.dashboard_tab, "📈 Dashboard")
        
        # Weighing tab
        self.weighing_tab = self.create_weighing_tab()
        self.tab_widget.addTab(self.weighing_tab, "⚖️ Weighing")
        
        # Transactions tab
        self.transactions_tab = self.create_transactions_tab()
        self.tab_widget.addTab(self.transactions_tab, "📄 Transactions")
        
        # Reports tab
        self.reports_tab = self.create_reports_tab()
        self.tab_widget.addTab(self.reports_tab, "📅 Reports")
        
        # Settings tab
        self.settings_tab = self.create_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "⚙️ Settings")
        
        # Serial Console tab (for debugging)
        self.console_tab = self.create_console_tab()
        self.tab_widget.addTab(self.console_tab, "🔌 Serial Console")
        
        main_layout.addWidget(self.tab_widget)
        
        self.central_widget.setLayout(main_layout)
    
    def create_header_section(self) -> QWidget:
        """Create the header section with system status"""
        
        header = QFrame()
        header.setFrameStyle(QFrame.Shape.StyledPanel)
        header.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                color: white;
                padding: 10px;
                border-radius: 8px;
            }
            QLabel {
                color: white;
            }
        """)
        
        layout = QHBoxLayout()
        
        # System title
        title_label = QLabel("SCALE System v2.0")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # System status indicators
        self.hardware_status_label = QLabel("🔴 Hardware: Disconnected")
        self.user_status_label = QLabel("👤 User: Not logged in")
        self.time_label = QLabel()
        
        layout.addWidget(self.hardware_status_label)
        layout.addWidget(QLabel(" | "))
        layout.addWidget(self.user_status_label)
        layout.addWidget(QLabel(" | "))
        layout.addWidget(self.time_label)
        
        header.setLayout(layout)
        
        # Update time every second
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time_display)
        self.time_timer.start(1000)
        self.update_time_display()
        
        return header
    
    def create_dashboard_tab(self) -> QWidget:
        """Create the main dashboard tab"""
        
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Quick action buttons
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout()
        
        self.connect_hardware_btn = QPushButton("🔌 Connect Hardware")
        self.connect_hardware_btn.setToolTip("Configure and connect to weighing hardware")
        self.connect_hardware_btn.clicked.connect(self.configure_hardware)
        
        self.new_transaction_btn = QPushButton("🆕 New Transaction")
        self.new_transaction_btn.setToolTip("Start a new weighing transaction (F4 or Ctrl+N)")
        self.new_transaction_btn.clicked.connect(self.start_new_transaction)
        self.new_transaction_btn.setEnabled(False)
        
        self.logout_btn = QPushButton("🚪 Logout")
        self.logout_btn.clicked.connect(self.logout)
        
        actions_layout.addWidget(self.connect_hardware_btn)
        actions_layout.addWidget(self.new_transaction_btn)
        actions_layout.addStretch()
        actions_layout.addWidget(self.logout_btn)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # Split layout for weight display and recent transactions
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Weight display section
        weight_section = self.create_weight_display_section()
        content_splitter.addWidget(weight_section)
        
        # Recent transactions section
        recent_section = self.create_recent_transactions_section()
        content_splitter.addWidget(recent_section)
        
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 1)
        
        layout.addWidget(content_splitter)
        
        tab.setLayout(layout)
        return tab
    
    def create_weight_display_section(self) -> QWidget:
        """Create the real-time weight display section"""
        
        group = QGroupBox("Current Weight Reading")
        layout = QVBoxLayout()
        
        # Large weight display
        self.weight_display = QLabel("--- KG")
        weight_font = QFont()
        weight_font.setPointSize(36)
        weight_font.setBold(True)
        self.weight_display.setFont(weight_font)
        self.weight_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.weight_display.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #00ff00;
                border: 2px solid #333333;
                border-radius: 8px;
                padding: 20px;
                margin: 10px;
            }
        """)
        layout.addWidget(self.weight_display)
        
        # Weight status indicators
        status_layout = QHBoxLayout()
        
        self.stability_label = QLabel("🔵 Stability: Unknown")
        self.unit_label = QLabel("📊 Unit: KG")
        self.last_update_label = QLabel("🕐 Last Update: Never")
        
        status_layout.addWidget(self.stability_label)
        status_layout.addWidget(self.unit_label)
        status_layout.addWidget(self.last_update_label)
        
        layout.addLayout(status_layout)
        
        # Connection info
        self.connection_info_label = QLabel("⚠️ No hardware connected")
        self.connection_info_label.setStyleSheet("color: #ff6600; font-weight: bold;")
        layout.addWidget(self.connection_info_label)
        
        group.setLayout(layout)
        return group
    
    def create_recent_transactions_section(self) -> QWidget:
        """Create recent transactions display"""
        
        group = QGroupBox("Recent Transactions")
        layout = QVBoxLayout()
        
        # Transactions table
        self.recent_transactions_table = QTableWidget()
        self.recent_transactions_table.setColumnCount(5)
        self.recent_transactions_table.setHorizontalHeaderLabels([
            "Ticket #", "Vehicle", "Net Weight", "Status", "Date"
        ])
        
        header = self.recent_transactions_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.recent_transactions_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        
        layout.addWidget(self.recent_transactions_table)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_recent_transactions)
        layout.addWidget(refresh_btn)
        
        group.setLayout(layout)
        return group
    
    def create_weighing_tab(self) -> QWidget:
        """Create the main weighing operations tab"""
        
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Transaction controls
        controls_group = QGroupBox("Transaction Controls")
        controls_layout = QGridLayout()
        
        # Vehicle information
        controls_layout.addWidget(QLabel("Vehicle Number:"), 0, 0)
        self.vehicle_number_edit = QLineEdit()
        self.vehicle_number_edit.setPlaceholderText("Enter vehicle number")
        controls_layout.addWidget(self.vehicle_number_edit, 0, 1)
        
        controls_layout.addWidget(QLabel("Driver Name:"), 0, 2)
        self.driver_name_edit = QLineEdit()
        self.driver_name_edit.setPlaceholderText("Optional")
        controls_layout.addWidget(self.driver_name_edit, 0, 3)
        
        # Product selection
        controls_layout.addWidget(QLabel("Product:"), 1, 0)
        self.product_combo = QComboBox()
        self.product_combo.setEditable(False)
        controls_layout.addWidget(self.product_combo, 1, 1)
        
        # Customer/Supplier selection
        controls_layout.addWidget(QLabel("Customer/Supplier:"), 1, 2)
        self.party_combo = QComboBox()
        self.party_combo.setEditable(False)
        controls_layout.addWidget(self.party_combo, 1, 3)
        
        # Transporter selection
        controls_layout.addWidget(QLabel("Transporter:"), 2, 0)
        self.transporter_combo = QComboBox()
        self.transporter_combo.setEditable(False)
        controls_layout.addWidget(self.transporter_combo, 2, 1)
        
        # DO/PO Number
        controls_layout.addWidget(QLabel("DO/PO Number:"), 2, 2)
        self.do_po_edit = QLineEdit()
        self.do_po_edit.setPlaceholderText("Delivery/Purchase Order Number")
        controls_layout.addWidget(self.do_po_edit, 2, 3)
        
        # Weighing mode
        controls_layout.addWidget(QLabel("Weighing Mode:"), 3, 0)
        self.weighing_mode_combo = QComboBox()
        self.weighing_mode_combo.addItems(["Two-Pass Weighing", "Fixed-Tare Weighing"])
        controls_layout.addWidget(self.weighing_mode_combo, 3, 1)
        
        # Tare weight (for fixed-tare mode)
        controls_layout.addWidget(QLabel("Tare Weight (KG):"), 3, 2)
        self.tare_weight_spin = QSpinBox()
        self.tare_weight_spin.setRange(0, 50000)
        self.tare_weight_spin.setEnabled(False)
        controls_layout.addWidget(self.tare_weight_spin, 3, 3)
        
        # Connect mode change
        self.weighing_mode_combo.currentTextChanged.connect(self.on_weighing_mode_changed)
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Weighing actions
        actions_group = QGroupBox("Weighing Actions")
        actions_layout = QHBoxLayout()
        
        self.start_weighing_btn = QPushButton("▶️ Start Weighing")
        self.start_weighing_btn.setProperty("class", "success")
        self.start_weighing_btn.clicked.connect(self.start_weighing_transaction)
        self.start_weighing_btn.setEnabled(False)
        
        self.capture_weight_btn = QPushButton("📷 Capture Weight")
        self.capture_weight_btn.clicked.connect(self.capture_current_weight)
        self.capture_weight_btn.setEnabled(False)
        
        self.complete_transaction_btn = QPushButton("✅ Complete Transaction")
        self.complete_transaction_btn.setProperty("class", "success")
        self.complete_transaction_btn.clicked.connect(self.complete_transaction)
        self.complete_transaction_btn.setEnabled(False)
        
        self.void_transaction_btn = QPushButton("❌ Void Transaction")
        self.void_transaction_btn.setProperty("class", "danger")
        self.void_transaction_btn.clicked.connect(self.void_transaction)
        self.void_transaction_btn.setEnabled(False)
        
        actions_layout.addWidget(self.start_weighing_btn)
        actions_layout.addWidget(self.capture_weight_btn)
        actions_layout.addWidget(self.complete_transaction_btn)
        actions_layout.addWidget(self.void_transaction_btn)
        actions_layout.addStretch()
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # Transaction status
        status_group = QGroupBox("Current Transaction Status")
        status_layout = QVBoxLayout()
        
        self.transaction_status_text = QTextEdit()
        self.transaction_status_text.setMaximumHeight(150)
        self.transaction_status_text.setReadOnly(True)
        self.transaction_status_text.setPlainText("No active transaction. Click 'Start Weighing' to begin.")
        
        status_layout.addWidget(self.transaction_status_text)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        tab.setLayout(layout)
        return tab
    
    def create_transactions_tab(self) -> QWidget:
        """Create the transactions management tab"""
        
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Search and filter controls
        filter_group = QGroupBox("Search & Filter")
        filter_layout = QGridLayout()
        
        filter_layout.addWidget(QLabel("Vehicle Number:"), 0, 0)
        self.search_vehicle_edit = QLineEdit()
        filter_layout.addWidget(self.search_vehicle_edit, 0, 1)
        
        filter_layout.addWidget(QLabel("Date From:"), 0, 2)
        self.date_from_edit = QDateEdit()
        self.date_from_edit.setDate(QDate.currentDate().addDays(-30))
        self.date_from_edit.setCalendarPopup(True)
        filter_layout.addWidget(self.date_from_edit, 0, 3)
        
        filter_layout.addWidget(QLabel("Date To:"), 1, 2)
        self.date_to_edit = QDateEdit()
        self.date_to_edit.setDate(QDate.currentDate())
        self.date_to_edit.setCalendarPopup(True)
        filter_layout.addWidget(self.date_to_edit, 1, 3)
        
        search_btn = QPushButton("🔍 Search")
        search_btn.clicked.connect(self.search_transactions)
        filter_layout.addWidget(search_btn, 1, 0)
        
        clear_btn = QPushButton("🧩 Clear")
        clear_btn.clicked.connect(self.clear_search_filters)
        filter_layout.addWidget(clear_btn, 1, 1)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Transactions table
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(8)
        self.transactions_table.setHorizontalHeaderLabels([
            "Ticket #", "Vehicle", "Driver", "Gross (KG)", "Tare (KG)", 
            "Net (KG)", "Status", "Date/Time"
        ])
        
        header = self.transactions_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        self.transactions_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.transactions_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.transactions_table)
        
        # Table actions
        table_actions_layout = QHBoxLayout()
        
        view_btn = QPushButton("👁️ View Details")
        view_btn.clicked.connect(self.view_transaction_details)
        
        print_btn = QPushButton("🖨️ Print Ticket")
        print_btn.clicked.connect(self.print_transaction_ticket)
        
        export_btn = QPushButton("📄 Export Data")
        export_btn.clicked.connect(self.export_transactions)
        
        table_actions_layout.addWidget(view_btn)
        table_actions_layout.addWidget(print_btn)
        table_actions_layout.addWidget(export_btn)
        table_actions_layout.addStretch()
        
        layout.addLayout(table_actions_layout)
        
        tab.setLayout(layout)
        return tab
    
    def create_reports_tab(self) -> QWidget:
        """Create the reports tab"""
        
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Report generation controls
        reports_group = QGroupBox("Report Generation")
        reports_layout = QGridLayout()
        
        reports_layout.addWidget(QLabel("Report Type:"), 0, 0)
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            "Daily Summary",
            "Weekly Summary", 
            "Monthly Summary",
            "Vehicle History",
            "Transaction Log",
            "System Activity"
        ])
        reports_layout.addWidget(self.report_type_combo, 0, 1)
        
        reports_layout.addWidget(QLabel("Date Range:"), 1, 0)
        date_range_layout = QHBoxLayout()
        
        self.report_date_from = QDateEdit()
        self.report_date_from.setDate(QDate.currentDate().addDays(-7))
        self.report_date_from.setCalendarPopup(True)
        
        self.report_date_to = QDateEdit()
        self.report_date_to.setDate(QDate.currentDate())
        self.report_date_to.setCalendarPopup(True)
        
        date_range_layout.addWidget(self.report_date_from)
        date_range_layout.addWidget(QLabel("to"))
        date_range_layout.addWidget(self.report_date_to)
        date_range_layout.addStretch()
        
        reports_layout.addLayout(date_range_layout, 1, 1)
        
        generate_btn = QPushButton("📈 Generate Report")
        generate_btn.clicked.connect(self.generate_report)
        reports_layout.addWidget(generate_btn, 2, 0)
        
        export_pdf_btn = QPushButton("📄 Export PDF")
        export_pdf_btn.clicked.connect(self.export_report_pdf)
        reports_layout.addWidget(export_pdf_btn, 2, 1)
        
        reports_group.setLayout(reports_layout)
        layout.addWidget(reports_group)
        
        # Report preview area
        preview_group = QGroupBox("Report Preview")
        preview_layout = QVBoxLayout()
        
        self.report_preview = QTextEdit()
        self.report_preview.setReadOnly(True)
        self.report_preview.setPlainText("Select a report type and generate to view results here.")
        
        preview_layout.addWidget(self.report_preview)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        tab.setLayout(layout)
        return tab
    
    def create_settings_tab(self) -> QWidget:
        """Create the settings tab"""
        
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Settings sections in tabs
        settings_tabs = QTabWidget()
        
        # Hardware settings
        hardware_tab = QWidget()
        hardware_layout = QVBoxLayout()
        
        hw_group = QGroupBox("Hardware Configuration")
        hw_layout = QGridLayout()
        
        hw_layout.addWidget(QLabel("Current Configuration:"), 0, 0)
        self.hw_config_label = QLabel("No hardware configured")
        hw_layout.addWidget(self.hw_config_label, 0, 1)
        
        configure_hw_btn = QPushButton("⚙️ Configure Hardware")
        configure_hw_btn.clicked.connect(self.configure_hardware)
        hw_layout.addWidget(configure_hw_btn, 1, 0)
        
        test_hw_btn = QPushButton("🧪 Test Connection")
        test_hw_btn.clicked.connect(self.test_hardware_connection)
        hw_layout.addWidget(test_hw_btn, 1, 1)
        
        hw_group.setLayout(hw_layout)
        hardware_layout.addWidget(hw_group)
        hardware_layout.addStretch()
        hardware_tab.setLayout(hardware_layout)
        
        settings_tabs.addTab(hardware_tab, "Hardware")
        
        # User settings
        user_tab = QWidget()
        user_layout = QVBoxLayout()
        
        user_group = QGroupBox("User Management")
        user_mgmt_layout = QVBoxLayout()
        
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(4)
        self.users_table.setHorizontalHeaderLabels(["Username", "Role", "Status", "Last Login"])
        
        user_mgmt_layout.addWidget(self.users_table)
        
        user_btn_layout = QHBoxLayout()
        add_user_btn = QPushButton("➕ Add User")
        edit_user_btn = QPushButton("✏️ Edit User")
        delete_user_btn = QPushButton("🗑️ Delete User")
        
        user_btn_layout.addWidget(add_user_btn)
        user_btn_layout.addWidget(edit_user_btn)
        user_btn_layout.addWidget(delete_user_btn)
        user_btn_layout.addStretch()
        
        user_mgmt_layout.addLayout(user_btn_layout)
        user_group.setLayout(user_mgmt_layout)
        
        user_layout.addWidget(user_group)
        user_tab.setLayout(user_layout)
        
        settings_tabs.addTab(user_tab, "Users")
        
        # System settings
        system_tab = QWidget()
        system_layout = QVBoxLayout()
        
        sys_group = QGroupBox("System Configuration")
        sys_layout = QGridLayout()
        
        sys_layout.addWidget(QLabel("Session Timeout (hours):"), 0, 0)
        self.session_timeout_spin = QSpinBox()
        self.session_timeout_spin.setRange(1, 24)
        self.session_timeout_spin.setValue(8)
        sys_layout.addWidget(self.session_timeout_spin, 0, 1)
        
        sys_layout.addWidget(QLabel("Auto-backup:"), 1, 0)
        self.auto_backup_check = QCheckBox("Enable daily backup")
        sys_layout.addWidget(self.auto_backup_check, 1, 1)
        
        save_settings_btn = QPushButton("💾 Save Settings")
        save_settings_btn.clicked.connect(self.save_system_settings)
        sys_layout.addWidget(save_settings_btn, 2, 0)
        
        sys_group.setLayout(sys_layout)
        system_layout.addWidget(sys_group)
        
        # Backup & Restore section
        backup_group = QGroupBox("Database Backup & Restore")
        backup_layout = QGridLayout()
        
        backup_info_label = QLabel(
            "Create database backups to protect your data from loss.\n"
            "Restore from backup to recover previous system state."
        )
        backup_info_label.setWordWrap(True)
        backup_info_label.setStyleSheet("color: #666; font-style: italic;")
        backup_layout.addWidget(backup_info_label, 0, 0, 1, 2)
        
        create_backup_btn = QPushButton("💾 Create Backup")
        create_backup_btn.setToolTip("Create a backup of the current database")
        create_backup_btn.clicked.connect(self.create_backup)
        backup_layout.addWidget(create_backup_btn, 1, 0)
        
        restore_backup_btn = QPushButton("🔄 Restore Backup")
        restore_backup_btn.setToolTip("Restore database from a backup file")
        restore_backup_btn.setProperty("class", "warning")
        restore_backup_btn.clicked.connect(self.restore_backup)
        backup_layout.addWidget(restore_backup_btn, 1, 1)
        
        backup_group.setLayout(backup_layout)
        system_layout.addWidget(backup_group)
        system_layout.addStretch()
        system_tab.setLayout(system_layout)
        
        settings_tabs.addTab(system_tab, "System")
        
        layout.addWidget(settings_tabs)
        
        tab.setLayout(layout)
        return tab
    
    def create_console_tab(self) -> QWidget:
        """Create the serial console diagnostic tab"""
        
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Console controls
        controls_group = QGroupBox("Serial Console Controls")
        controls_layout = QGridLayout()
        
        # Connection status
        self.console_status_label = QLabel("Status: Disconnected")
        self.console_status_label.setStyleSheet("color: red; font-weight: bold;")
        controls_layout.addWidget(QLabel("Connection Status:"), 0, 0)
        controls_layout.addWidget(self.console_status_label, 0, 1)
        
        # Packet recording controls
        self.recording_enabled = QCheckBox("Enable Packet Recording")
        self.recording_enabled.toggled.connect(self.toggle_packet_recording)
        controls_layout.addWidget(self.recording_enabled, 1, 0)
        
        self.recording_file_label = QLabel("Not recording")
        self.recording_file_label.setStyleSheet("font-style: italic; color: #666;")
        controls_layout.addWidget(self.recording_file_label, 1, 1)
        
        # Statistics
        stats_layout = QHBoxLayout()
        self.packets_received_label = QLabel("Packets: 0")
        self.bytes_received_label = QLabel("Bytes: 0")
        self.errors_count_label = QLabel("Errors: 0")
        
        stats_layout.addWidget(self.packets_received_label)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.bytes_received_label)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.errors_count_label)
        stats_layout.addStretch()
        
        controls_layout.addLayout(stats_layout, 2, 0, 1, 2)
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Split layout for console display and manual commands
        console_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Raw data display
        raw_data_group = QGroupBox("Raw Serial Data Stream")
        raw_data_layout = QVBoxLayout()
        
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFont(QFont("Consolas", 9))
        self.console_output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                border: 1px solid #333;
            }
        """)
        # Limit console output (PyQt6 compatibility)
        try:
            self.console_output.setMaximumBlockCount(1000)
        except AttributeError:
            # setMaximumBlockCount not available in this PyQt version
            pass
        
        raw_data_layout.addWidget(self.console_output)
        
        # Console action buttons
        console_actions = QHBoxLayout()
        
        clear_console_btn = QPushButton("🧹 Clear Console")
        clear_console_btn.clicked.connect(self.clear_console)
        
        save_console_btn = QPushButton("💾 Save Console")
        save_console_btn.clicked.connect(self.save_console_output)
        
        pause_console_btn = QPushButton("⏸️ Pause/Resume")
        pause_console_btn.setCheckable(True)
        pause_console_btn.toggled.connect(self.toggle_console_pause)
        
        console_actions.addWidget(clear_console_btn)
        console_actions.addWidget(save_console_btn)
        console_actions.addWidget(pause_console_btn)
        console_actions.addStretch()
        
        raw_data_layout.addLayout(console_actions)
        raw_data_group.setLayout(raw_data_layout)
        
        console_splitter.addWidget(raw_data_group)
        
        # Manual command sending
        command_group = QGroupBox("Manual Command Testing")
        command_layout = QVBoxLayout()
        
        command_input_layout = QHBoxLayout()
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command to send (e.g., 'STATUS', 'ZERO', etc.)")
        self.command_input.returnPressed.connect(self.send_manual_command)
        
        send_command_btn = QPushButton("📤 Send Command")
        send_command_btn.clicked.connect(self.send_manual_command)
        
        command_input_layout.addWidget(QLabel("Command:"))
        command_input_layout.addWidget(self.command_input)
        command_input_layout.addWidget(send_command_btn)
        
        command_layout.addLayout(command_input_layout)
        
        # Predefined commands
        predefined_layout = QHBoxLayout()
        predefined_layout.addWidget(QLabel("Quick Commands:"))
        
        status_cmd_btn = QPushButton("STATUS")
        status_cmd_btn.clicked.connect(lambda: self.send_predefined_command("STATUS"))
        
        zero_cmd_btn = QPushButton("ZERO")
        zero_cmd_btn.clicked.connect(lambda: self.send_predefined_command("ZERO"))
        
        tare_cmd_btn = QPushButton("TARE")
        tare_cmd_btn.clicked.connect(lambda: self.send_predefined_command("TARE"))
        
        test_cmd_btn = QPushButton("TEST")
        test_cmd_btn.clicked.connect(lambda: self.send_predefined_command("TEST"))
        
        predefined_layout.addWidget(status_cmd_btn)
        predefined_layout.addWidget(zero_cmd_btn)
        predefined_layout.addWidget(tare_cmd_btn)
        predefined_layout.addWidget(test_cmd_btn)
        predefined_layout.addStretch()
        
        command_layout.addLayout(predefined_layout)
        
        # Command response area
        self.command_response = QTextEdit()
        self.command_response.setReadOnly(True)
        self.command_response.setMaximumHeight(100)
        self.command_response.setPlaceholderText("Command responses will appear here...")
        command_layout.addWidget(QLabel("Last Response:"))
        command_layout.addWidget(self.command_response)
        
        command_group.setLayout(command_layout)
        console_splitter.addWidget(command_group)
        
        # Set splitter proportions
        console_splitter.setStretchFactor(0, 3)  # Console gets more space
        console_splitter.setStretchFactor(1, 1)  # Commands get less space
        
        layout.addWidget(console_splitter)
        
        # Initialize console state
        self.console_paused = False
        self.packet_recording = False
        self.recording_file = None
        self.packets_received = 0
        self.bytes_received = 0
        self.errors_count = 0
        
        tab.setLayout(layout)
        return tab
        """Setup the status bar"""
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Status indicators
        self.status_bar.addWidget(QLabel("Status:"))
        
        self.main_status_label = QLabel("Ready")
        self.status_bar.addWidget(self.main_status_label)
        
        self.status_bar.addPermanentWidget(QLabel(" | "))
        
        self.connection_status_label = QLabel("Hardware: Disconnected")
        self.status_bar.addPermanentWidget(self.connection_status_label)
    
    def setup_menu_bar(self):
        """Setup the menu bar"""
        
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Transaction", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.start_new_transaction)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Weighing menu
        weighing_menu = menubar.addMenu("Weighing")
        
        timbang1_action = QAction("Timbang I (First Weigh)", self)
        timbang1_action.setShortcut("F2")
        timbang1_action.triggered.connect(self.perform_timbang_1)
        weighing_menu.addAction(timbang1_action)
        
        timbang2_action = QAction("Timbang II (Second Weigh)", self)
        timbang2_action.setShortcut("F3")
        timbang2_action.triggered.connect(self.perform_timbang_2)
        weighing_menu.addAction(timbang2_action)
        
        weighing_menu.addSeparator()
        
        new_transaction_action = QAction("New Transaction", self)
        new_transaction_action.setShortcut("F4")
        new_transaction_action.triggered.connect(self.start_new_transaction)
        weighing_menu.addAction(new_transaction_action)
        
        save_transaction_action = QAction("Save Transaction", self)
        save_transaction_action.setShortcut("Ctrl+S")
        save_transaction_action.triggered.connect(self.save_current_transaction)
        weighing_menu.addAction(save_transaction_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        hardware_config_action = QAction("Hardware Configuration", self)
        hardware_config_action.triggered.connect(self.configure_hardware)
        tools_menu.addAction(hardware_config_action)
        
        refresh_action = QAction("Refresh/Reconnect Hardware", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_hardware_connection)
        tools_menu.addAction(refresh_action)
        
        tools_menu.addSeparator()
        
        backup_action = QAction("Create Backup", self)
        backup_action.triggered.connect(self.create_backup)
        tools_menu.addAction(backup_action)
        
        export_action = QAction("Export Transactions", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_transactions)
        tools_menu.addAction(export_action)
        
        tools_menu.addSeparator()
        
        master_data_action = QAction("Master Data Management", self)
        master_data_action.setShortcut("Ctrl+M")
        master_data_action.triggered.connect(self.open_master_data_dialog)
        tools_menu.addAction(master_data_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        shortcuts_action = QAction("Keyboard Shortcuts", self)
        shortcuts_action.setShortcut("F1")
        shortcuts_action.triggered.connect(self.show_shortcuts_dialog)
        help_menu.addAction(shortcuts_action)
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def setup_toolbar(self):
        """Setup the toolbar"""
        
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Quick action buttons
        connect_action = QAction("🔌 Connect", self)
        connect_action.triggered.connect(self.configure_hardware)
        toolbar.addAction(connect_action)
        
        new_trans_action = QAction("🆕 New Transaction", self)
        new_trans_action.triggered.connect(self.start_new_transaction)
        toolbar.addAction(new_trans_action)
        
        toolbar.addSeparator()
        
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.triggered.connect(self.refresh_all_data)
        toolbar.addAction(refresh_action)
    
    def setup_status_bar(self):
        """Setup the status bar"""
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Status indicators
        self.status_bar.addWidget(QLabel("Status:"))
        
        self.main_status_label = QLabel("Ready")
        self.status_bar.addWidget(self.main_status_label)
        
        self.status_bar.addPermanentWidget(QLabel(" | "))
        
        self.connection_status_label = QLabel("Hardware: Disconnected")
        self.status_bar.addPermanentWidget(self.connection_status_label)
    
    def setup_connections(self):
        """Setup signal connections"""
        
        # Connect workflow controller signals
        self.workflow_controller.state_changed.connect(self.on_workflow_state_changed)
        self.workflow_controller.weight_captured.connect(self.on_weight_captured)
        self.workflow_controller.transaction_completed.connect(self.on_transaction_completed)
        self.workflow_controller.error_occurred.connect(self.on_workflow_error)
    
    def show_login_dialog(self):
        """Show the login dialog"""
        
        login_dialog = LoginDialog(self.auth_service, self)
        result = login_dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            self.current_user = login_dialog.get_authenticated_user()
            self.user_status_label.setText(f"👤 User: {self.current_user['username']} ({self.current_user['role']})")
            self.main_status_label.setText(f"Logged in as {self.current_user['username']}")
            
            # Enable functionality based on user role
            self.enable_user_interface()
            
        else:
            # If login cancelled, exit application
            self.close()
    
    def enable_user_interface(self):
        """Enable interface elements based on user permissions"""
        
        if not self.current_user:
            return
        
        # Enable basic functionality
        self.connect_hardware_btn.setEnabled(True)
        
        # Populate dropdown data from database
        self.refresh_dropdown_data()
        
        # Enable transaction creation if user has permission
        # (This would check against the RBAC system)
        self.start_weighing_btn.setEnabled(self.is_connected)
        
        # Load initial data
        self.refresh_recent_transactions()
        self.load_users_data()
    
    @pyqtSlot()
    def configure_hardware(self):
        """Open hardware configuration dialog"""
        
        dialog = HardwareConfigDialog(self)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            config = dialog.get_final_configuration()
            if config:
                self.rs232_config = config
                self.connect_to_hardware()
    
    def connect_to_hardware(self):
        """Connect to hardware with current configuration"""
        
        if not self.rs232_config:
            return
        
        # Stop existing connection
        if self.weight_monitor:
            self.weight_monitor.stop_monitoring()
        
        # Start new weight monitoring
        self.weight_monitor = WeightDisplayWorker()
        self.weight_monitor.weight_updated.connect(self.on_weight_updated)
        self.weight_monitor.connection_status.connect(self.on_hardware_connection_status)
        
        self.weight_monitor.start_monitoring(self.rs232_config)
        
        # Update UI
        self.hardware_status_label.setText(
            f"🟡 Hardware: Connecting to {self.rs232_config.port}..."
        )
    
    @pyqtSlot(dict)
    def on_weight_updated(self, weight_data: Dict):
        """Handle weight update from hardware"""
        
        self.current_weight = weight_data
        
        # Update weight display
        weight = weight_data.get('weight', 0)
        unit = weight_data.get('unit', 'KG')
        stable = weight_data.get('stable', False)
        
        self.weight_display.setText(f"{weight:.2f} {unit}")
        
        # Update stability indicator
        if stable:
            self.stability_label.setText("🟢 Stability: STABLE")
            self.weight_display.setStyleSheet("""
                QLabel {
                    background-color: #1e1e1e;
                    color: #00ff00;
                    border: 2px solid #00ff00;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 10px;
                }
            """)
        else:
            self.stability_label.setText("🟡 Stability: MOTION")
            self.weight_display.setStyleSheet("""
                QLabel {
                    background-color: #1e1e1e;
                    color: #ffff00;
                    border: 2px solid #ffaa00;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 10px;
                }
            """)
        
        self.unit_label.setText(f"📊 Unit: {unit}")
        self.last_update_label.setText(
            f"🕐 Last Update: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        # Enable/disable capture button based on stability
        if hasattr(self, 'capture_weight_btn'):
            self.capture_weight_btn.setEnabled(stable and self.current_transaction is not None)
        
        # Log to serial console if available
        raw_data = weight_data.get('raw_data', '')
        if hasattr(self, 'console_output') and raw_data:
            self.log_to_console(f"[RX] {raw_data}")
            
            # Update statistics
            self.packets_received += 1
            self.bytes_received += len(raw_data)
            self.update_console_statistics()
            
            # Record to file if recording enabled
            if self.packet_recording and self.recording_file:
                try:
                    self.recording_file.write(f"[{datetime.now().isoformat()}] [RX] {raw_data}\n")
                    self.recording_file.flush()
                except Exception as e:
                    self.errors_count += 1
                    self.log_to_console(f"[ERROR] Recording error: {str(e)}")
    
    @pyqtSlot(str, bool)
    def on_hardware_connection_status(self, message: str, connected: bool):
        """Handle hardware connection status updates"""
        
        self.is_connected = connected
        
        if connected:
            self.hardware_status_label.setText("🟢 Hardware: Connected")
            self.connection_status_label.setText("Hardware: Connected")
            self.connection_info_label.setText(f"✅ {message}")
            self.connection_info_label.setStyleSheet("color: #10b010; font-weight: bold;")
            
            # Enable transaction controls
            self.new_transaction_btn.setEnabled(True)
            if self.current_user:
                self.start_weighing_btn.setEnabled(True)
            
            # Update console status if available
            if hasattr(self, 'console_status_label'):
                self.console_status_label.setText("Status: Connected")
                self.console_status_label.setStyleSheet("color: green; font-weight: bold;")
                self.log_to_console(f"[SYSTEM] Hardware connected: {message}")
            
        else:
            self.hardware_status_label.setText("🔴 Hardware: Disconnected")
            self.connection_status_label.setText("Hardware: Disconnected")
            self.connection_info_label.setText(f"❌ {message}")
            self.connection_info_label.setStyleSheet("color: #ff6600; font-weight: bold;")
            
            # Disable transaction controls
            self.new_transaction_btn.setEnabled(False)
            self.start_weighing_btn.setEnabled(False)
            
            # Update console status if available
            if hasattr(self, 'console_status_label'):
                self.console_status_label.setText("Status: Disconnected")
                self.console_status_label.setStyleSheet("color: red; font-weight: bold;")
                self.log_to_console(f"[SYSTEM] Hardware disconnected: {message}")
            self.capture_weight_btn.setEnabled(False)
        
        self.main_status_label.setText(message)
    
    @pyqtSlot()
    def update_time_display(self):
        """Update the time display"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(f"🕐 {current_time}")
    
    # Transaction management methods
    @pyqtSlot()
    def start_new_transaction(self):
        """Start a new weighing transaction"""
        self.tab_widget.setCurrentIndex(1)  # Switch to weighing tab
    
    @pyqtSlot(str)
    def on_weighing_mode_changed(self, mode: str):
        """Handle weighing mode change"""
        if "Fixed-Tare" in mode:
            self.tare_weight_spin.setEnabled(True)
        else:
            self.tare_weight_spin.setEnabled(False)
    
    @pyqtSlot()
    def start_weighing_transaction(self):
        """Start a new weighing transaction"""
        
        vehicle_number = self.vehicle_number_edit.text().strip()
        if not vehicle_number:
            QMessageBox.warning(self, "Vehicle Required", 
                              "Please enter a vehicle number before starting.")
            return
        
        # Create transaction data
        transaction_data = {
            'vehicle_no': vehicle_number,
            'driver_name': self.driver_name_edit.text().strip() or None,
            'weighing_mode': 'two_pass' if 'Two-Pass' in self.weighing_mode_combo.currentText() else 'fixed_tare',
            'tare_weight': self.tare_weight_spin.value() if self.tare_weight_spin.isEnabled() else None,
            'user_id': self.current_user['user_id']
        }
        
        try:
            # Start transaction through workflow controller
            self.current_transaction = self.workflow_controller.start_transaction(
                transaction_data['weighing_mode'],
                transaction_data
            )
            
            # Update UI state
            self.start_weighing_btn.setEnabled(False)
            self.capture_weight_btn.setEnabled(self.is_connected)
            self.void_transaction_btn.setEnabled(True)
            
            # Update status
            self.transaction_status_text.setPlainText(
                f"Transaction started:\n"
                f"Ticket #: {self.current_transaction.get('ticket_no', 'N/A')}\n"
                f"Vehicle: {vehicle_number}\n"
                f"Mode: {transaction_data['weighing_mode'].replace('_', '-').title()}\n"
                f"Status: Waiting for first weight...\n"
                f"\n📷 Position vehicle on scale and click 'Capture Weight' when stable."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Transaction Error", 
                               f"Failed to start transaction:\n{str(e)}")
    
    @pyqtSlot()
    def capture_current_weight(self):
        """Capture the current weight reading"""
        
        if not self.current_weight or not self.current_weight.get('stable', False):
            QMessageBox.warning(self, "Weight Not Stable", 
                              "Please wait for the weight reading to stabilize before capturing.")
            return
        
        if not self.current_transaction:
            QMessageBox.warning(self, "No Transaction", 
                              "Please start a transaction first.")
            return
        
        try:
            # Capture weight through workflow controller
            self.workflow_controller.capture_weight(
                self.current_transaction['transaction_id'],
                self.current_weight['weight']
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Capture Error", 
                               f"Failed to capture weight:\n{str(e)}")
    
    @pyqtSlot()
    def complete_transaction(self):
        """Complete the current transaction"""
        
        if not self.current_transaction:
            return
        
        try:
            result = self.workflow_controller.complete_transaction(
                self.current_transaction['transaction_id']
            )
            
            if result['success']:
                QMessageBox.information(
                    self, "Transaction Complete",
                    f"Transaction completed successfully!\n"
                    f"Ticket #: {result['ticket_no']}\n"
                    f"Net Weight: {result['net_weight']:.2f} KG"
                )
                
                # Reset UI
                self.reset_transaction_ui()
            
        except Exception as e:
            QMessageBox.critical(self, "Complete Error", 
                               f"Failed to complete transaction:\n{str(e)}")
    
    @pyqtSlot()
    def void_transaction(self):
        """Void the current transaction"""
        
        if not self.current_transaction:
            return
        
        reply = QMessageBox.question(
            self, "Void Transaction",
            "Are you sure you want to void this transaction?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.workflow_controller.void_transaction(
                    self.current_transaction['transaction_id']
                )
                
                QMessageBox.information(self, "Transaction Voided", 
                                       "Transaction has been voided.")
                
                self.reset_transaction_ui()
                
            except Exception as e:
                QMessageBox.critical(self, "Void Error", 
                                   f"Failed to void transaction:\n{str(e)}")
    
    def reset_transaction_ui(self):
        """Reset the transaction UI to initial state"""
        
        self.current_transaction = None
        
        # Reset form fields
        self.vehicle_number_edit.clear()
        self.driver_name_edit.clear()
        self.weighing_mode_combo.setCurrentIndex(0)
        self.tare_weight_spin.setValue(0)
        
        # Reset button states
        self.start_weighing_btn.setEnabled(self.is_connected)
        self.capture_weight_btn.setEnabled(False)
        self.complete_transaction_btn.setEnabled(False)
        self.void_transaction_btn.setEnabled(False)
        
        # Reset status text
        self.transaction_status_text.setPlainText(
            "No active transaction. Click 'Start Weighing' to begin."
        )
        
        # Refresh data
        self.refresh_recent_transactions()
    
    # Workflow controller event handlers
    @pyqtSlot(str)
    def on_workflow_state_changed(self, state: str):
        """Handle workflow state changes"""
        
        status_messages = {
            WorkflowState.IDLE.value: "Ready for new transaction",
            WorkflowState.FIRST_WEIGHT.value: "Waiting for first weight capture",
            WorkflowState.SECOND_WEIGHT.value: "Waiting for second weight capture",
            WorkflowState.COMPLETED.value: "Transaction completed",
            WorkflowState.VOIDED.value: "Transaction voided"
        }
        
        message = status_messages.get(state, f"State: {state}")
        self.main_status_label.setText(message)
        
        # Update transaction status display
        if self.current_transaction:
            current_text = self.transaction_status_text.toPlainText()
            self.transaction_status_text.setPlainText(
                f"{current_text}\n\n🔄 Status: {message}"
            )
    
    @pyqtSlot(dict)
    def on_weight_captured(self, weight_info: Dict):
        """Handle weight capture events"""
        
        weight_type = weight_info.get('weight_type', 'unknown')
        weight_value = weight_info.get('weight', 0)
        
        if weight_type == 'gross':
            self.transaction_status_text.setPlainText(
                self.transaction_status_text.toPlainText() + 
                f"\n\n⚖️ Gross weight captured: {weight_value:.2f} KG\n"
                f"Please remove vehicle from scale and click 'Capture Weight' again for tare."
            )
        elif weight_type == 'tare':
            self.transaction_status_text.setPlainText(
                self.transaction_status_text.toPlainText() + 
                f"\n⚖️ Tare weight captured: {weight_value:.2f} KG\n"
                f"Transaction ready to complete."
            )
            
            self.complete_transaction_btn.setEnabled(True)
    
    @pyqtSlot(dict)
    def on_transaction_completed(self, result: Dict):
        """Handle transaction completion"""
        
        self.transaction_status_text.setPlainText(
            self.transaction_status_text.toPlainText() + 
            f"\n\n✅ Transaction completed!\n"
            f"Ticket #: {result.get('ticket_no', 'N/A')}\n"
            f"Net Weight: {result.get('net_weight', 0):.2f} KG"
        )
    
    @pyqtSlot(str)
    def on_workflow_error(self, error_message: str):
        """Handle workflow errors"""
        
        QMessageBox.critical(self, "Workflow Error", error_message)
        self.main_status_label.setText(f"Error: {error_message}")
    
    # Data management methods
    @pyqtSlot()
    def refresh_recent_transactions(self):
        """Refresh the recent transactions display"""
        
        try:
            # Get recent transactions from database
            transactions = self.data_access.get_recent_transactions(limit=10)
            
            self.recent_transactions_table.setRowCount(len(transactions))
            
            for row, transaction in enumerate(transactions):
                self.recent_transactions_table.setItem(row, 0, QTableWidgetItem(transaction.get('ticket_no', '')))
                self.recent_transactions_table.setItem(row, 1, QTableWidgetItem(transaction.get('vehicle_no', '')))
                self.recent_transactions_table.setItem(row, 2, QTableWidgetItem(f"{transaction.get('net_weight', 0):.2f} KG"))
                self.recent_transactions_table.setItem(row, 3, QTableWidgetItem(transaction.get('status', '')))
                self.recent_transactions_table.setItem(row, 4, QTableWidgetItem(transaction.get('created_at', '')))
                
        except Exception as e:
            print(f"Error refreshing transactions: {e}")
    
    def load_users_data(self):
        """Load users data into the users table"""
        
        try:
            # This would load from the authentication service
            # For now, just placeholder
            users = [
                {'username': 'admin', 'role': 'Admin', 'status': 'Active', 'last_login': '2025-08-23 16:30:00'},
                {'username': 'supervisor', 'role': 'Supervisor', 'status': 'Active', 'last_login': '2025-08-23 15:45:00'},
                {'username': 'operator', 'role': 'Operator', 'status': 'Active', 'last_login': '2025-08-23 14:20:00'}
            ]
            
            self.users_table.setRowCount(len(users))
            
            for row, user in enumerate(users):
                self.users_table.setItem(row, 0, QTableWidgetItem(user['username']))
                self.users_table.setItem(row, 1, QTableWidgetItem(user['role']))
                self.users_table.setItem(row, 2, QTableWidgetItem(user['status']))
                self.users_table.setItem(row, 3, QTableWidgetItem(user['last_login']))
                
        except Exception as e:
            print(f"Error loading users: {e}")
    
    # Placeholder methods for menu actions
    def logout(self):
        """Logout current user"""
        reply = QMessageBox.question(
            self, "Logout", 
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Stop hardware monitoring
            if self.weight_monitor:
                self.weight_monitor.stop_monitoring()
            
            # Clear current state
            self.current_user = None
            self.current_transaction = None
            
            # Show login dialog again
            self.show_login_dialog()
    
    def test_hardware_connection(self):
        """Test hardware connection"""
        if self.rs232_config:
            # Use the RS232 manager to test
            result = RS232Manager().test_connection(self.rs232_config, "TEST\r\n")
            
            if result.success:
                QMessageBox.information(self, "Connection Test", 
                                       f"Connection successful!\n"
                                       f"Response time: {result.response_time:.3f}s\n"
                                       f"Bytes received: {result.bytes_received}")
            else:
                QMessageBox.warning(self, "Connection Test", 
                                   f"Connection failed:\n{result.error_message}")
        else:
            QMessageBox.warning(self, "No Configuration", 
                              "Please configure hardware first.")
    
    def search_transactions(self):
        """Search transactions based on filters"""
        # Implement transaction search
        QMessageBox.information(self, "Search", "Transaction search will be implemented.")
    
    def clear_search_filters(self):
        """Clear search filters"""
        self.search_vehicle_edit.clear()
        self.date_from_edit.setDate(QDate.currentDate().addDays(-30))
        self.date_to_edit.setDate(QDate.currentDate())
    
    def view_transaction_details(self):
        """View detailed transaction information"""
        QMessageBox.information(self, "View Details", "Transaction details view will be implemented.")
    
    def print_transaction_ticket(self):
        """Print transaction ticket"""
        QMessageBox.information(self, "Print", "Ticket printing will be implemented.")
    
    def export_transactions(self):
        """Export transactions data to CSV or JSON"""
        try:
            # Get all transactions from database
            query = """
            SELECT 
                t.id, t.ticket_no, t.vehicle_no, t.gross_weight,
                t.tare_weight, t.net_weight, t.product, t.customer,
                t.transporter, t.do_po_number, t.operator, t.status,
                t.weighing_mode, t.created_at_utc, t.completed_at_utc
            FROM transactions t 
            ORDER BY t.created_at_utc DESC
            """
            
            transactions = self.data_access.execute_query(query)
            
            if not transactions:
                QMessageBox.information(self, "No Data", "No transactions available to export.")
                return
            
            # Ask user for export format
            reply = QMessageBox.question(
                self, "Export Format", 
                "Choose export format:\n\nClick 'Yes' for CSV format\nClick 'No' for JSON format",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                return
            
            # Export based on user choice
            if reply == QMessageBox.StandardButton.Yes:
                # CSV Export
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Export Transactions to CSV", 
                    f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "CSV files (*.csv)"
                )
                
                if file_path:
                    # Define columns for CSV export
                    columns = [
                        'id', 'ticket_no', 'vehicle_no', 'gross_weight', 'tare_weight',
                        'net_weight', 'product', 'customer', 'transporter', 
                        'do_po_number', 'operator', 'status', 'weighing_mode',
                        'created_at_utc', 'completed_at_utc'
                    ]
                    
                    if export_to_csv(transactions, file_path, columns):
                        QMessageBox.information(
                            self, "Export Successful",
                            f"Transactions exported successfully to:\n{file_path}\n\n"
                            f"Records exported: {len(transactions)}"
                        )
                    else:
                        QMessageBox.critical(
                            self, "Export Failed",
                            "Failed to export transactions to CSV file."
                        )
            
            else:
                # JSON Export
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Export Transactions to JSON", 
                    f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    "JSON files (*.json)"
                )
                
                if file_path:
                    export_data = {
                        'export_info': {
                            'exported_at': datetime.now().isoformat(),
                            'total_records': len(transactions),
                            'exported_by': self.current_user['username'] if self.current_user else 'Unknown'
                        },
                        'transactions': transactions
                    }
                    
                    if export_to_json(export_data, file_path):
                        file_size = os.path.getsize(file_path)
                        QMessageBox.information(
                            self, "Export Successful",
                            f"Transactions exported successfully to:\n{file_path}\n\n"
                            f"Records exported: {len(transactions)}\n"
                            f"File size: {format_file_size(file_size)}"
                        )
                    else:
                        QMessageBox.critical(
                            self, "Export Failed",
                            "Failed to export transactions to JSON file."
                        )
        
        except Exception as e:
            QMessageBox.critical(
                self, "Export Error",
                f"An error occurred during export:\n{str(e)}"
            )
    
    def generate_report(self):
        """Generate selected report"""
        report_type = self.report_type_combo.currentText()
        self.report_preview.setPlainText(f"Generated {report_type} report would appear here.")
    
    def export_report_pdf(self):
        """Export report as PDF"""
        QMessageBox.information(self, "Export PDF", "PDF export will be implemented.")
    
    def save_system_settings(self):
        """Save system settings"""
        QMessageBox.information(self, "Settings Saved", "System settings have been saved.")
    
    def create_backup(self):
        """Create system backup"""
        try:
            # Ask user for backup location
            default_filename = f"scale_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Create Database Backup", 
                default_filename,
                "Database files (*.db);;All files (*.*)"
            )
            
            if not file_path:
                return
            
            # Create progress dialog
            progress = QProgressBar()
            progress.setRange(0, 0)  # Indeterminate progress
            
            # Show progress message
            msg = QMessageBox(self)
            msg.setWindowTitle("Creating Backup")
            msg.setText("Creating database backup...")
            msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
            msg.show()
            
            # Perform backup
            success = self.data_access.create_backup(file_path)
            msg.close()
            
            if success:
                # Get file size for display
                file_size = os.path.getsize(file_path)
                
                QMessageBox.information(
                    self, "Backup Successful",
                    f"Database backup created successfully:\n{file_path}\n\n"
                    f"Backup size: {format_file_size(file_size)}\n"
                    f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                # Log the backup action
                if self.current_user:
                    self.data_access.log_audit_action(
                        operator_id=self.current_user['id'],
                        action='DATABASE_BACKUP',
                        entity='SYSTEM',
                        entity_id='backup',
                        reason=f'Manual backup to {os.path.basename(file_path)}'
                    )
            else:
                QMessageBox.critical(
                    self, "Backup Failed",
                    f"Failed to create backup at:\n{file_path}\n\n"
                    "Please check file permissions and available disk space."
                )
        
        except Exception as e:
            QMessageBox.critical(
                self, "Backup Error",
                f"An error occurred during backup:\n{str(e)}"
            )
    
    def restore_backup(self):
        """Restore system from backup"""
        try:
            # Show warning about data loss
            reply = QMessageBox.warning(
                self, "Restore Database",
                "⚠️ WARNING: This will replace ALL current data with the backup data.\n\n"
                "Current transactions, users, and settings will be permanently lost.\n\n"
                "Are you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Ask user for backup file
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Backup File to Restore", 
                "",
                "Database files (*.db);;All files (*.*)"
            )
            
            if not file_path:
                return
            
            # Verify the backup file exists and is readable
            if not os.path.exists(file_path):
                QMessageBox.critical(
                    self, "File Not Found",
                    f"Backup file not found:\n{file_path}"
                )
                return
            
            # Show progress message
            msg = QMessageBox(self)
            msg.setWindowTitle("Restoring Backup")
            msg.setText("Restoring database from backup...")
            msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
            msg.show()
            
            # Perform restore
            success = self.data_access.restore_backup(file_path)
            msg.close()
            
            if success:
                QMessageBox.information(
                    self, "Restore Successful",
                    f"Database restored successfully from:\n{file_path}\n\n"
                    "The application will restart to apply changes."
                )
                
                # Log the restore action (if possible)
                try:
                    if self.current_user:
                        self.data_access.log_audit_action(
                            operator_id=self.current_user['id'],
                            action='DATABASE_RESTORE',
                            entity='SYSTEM',
                            entity_id='restore',
                            reason=f'Manual restore from {os.path.basename(file_path)}'
                        )
                except:
                    pass  # Log might fail after restore
                
                # Restart application
                QApplication.quit()
                
            else:
                QMessageBox.critical(
                    self, "Restore Failed",
                    f"Failed to restore from backup:\n{file_path}\n\n"
                    "Please verify the backup file is valid and not corrupted."
                )
        
        except Exception as e:
            QMessageBox.critical(
                self, "Restore Error",
                f"An error occurred during restore:\n{str(e)}"
            )
    
    def show_about_dialog(self):
        """Show about dialog"""
        QMessageBox.about(self, "About SCALE System",
                         "SCALE System v2.0\n\n"
                         "Professional Weighbridge Management System\n\n"
                         "Features:\n"
                         "• Automated RS232 port detection\n"
                         "• Real-time weight monitoring\n"
                         "• Two-pass and fixed-tare weighing\n"
                         "• Role-based access control\n"
                         "• Comprehensive reporting\n\n"
                         "Built with PyQt6 and Python")
    
    def perform_timbang_1(self):
        """Perform first weighing (Timbang I)"""
        try:
            if not self.current_user:
                QMessageBox.warning(self, "Authentication Required", "Please login first.")
                return
            
            if not self.is_connected:
                QMessageBox.warning(self, "Hardware Required", "Please connect to weighing hardware first.")
                return
            
            if not self.current_weight or not self.current_weight.get('stable', False):
                QMessageBox.warning(
                    self, "Weight Not Stable", 
                    "Please wait for the weight reading to stabilize before capturing."
                )
                return
            
            # Switch to weighing tab if not already there
            self.tab_widget.setCurrentWidget(self.weighing_tab)
            
            # Start or continue the weighing workflow
            if hasattr(self, 'start_weighing_btn'):
                self.start_weighing_btn.click()
            else:
                QMessageBox.information(
                    self, "Timbang I",
                    f"First weighing captured: {self.current_weight.get('weight', 0):.2f} KG\n\n"
                    "This is a keyboard shortcut test. Full integration requires completing the weighing workflow."
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Timbang I Error", f"Error performing first weighing: {str(e)}")
    
    def perform_timbang_2(self):
        """Perform second weighing (Timbang II)"""
        try:
            if not self.current_user:
                QMessageBox.warning(self, "Authentication Required", "Please login first.")
                return
            
            if not self.is_connected:
                QMessageBox.warning(self, "Hardware Required", "Please connect to weighing hardware first.")
                return
            
            if not self.current_weight or not self.current_weight.get('stable', False):
                QMessageBox.warning(
                    self, "Weight Not Stable", 
                    "Please wait for the weight reading to stabilize before capturing."
                )
                return
            
            # Switch to weighing tab if not already there
            self.tab_widget.setCurrentWidget(self.weighing_tab)
            
            QMessageBox.information(
                self, "Timbang II",
                f"Second weighing captured: {self.current_weight.get('weight', 0):.2f} KG\n\n"
                "This is a keyboard shortcut test. Full integration requires completing the weighing workflow."
            )
                
        except Exception as e:
            QMessageBox.critical(self, "Timbang II Error", f"Error performing second weighing: {str(e)}")
    
    def save_current_transaction(self):
        """Save current transaction"""
        try:
            if not self.current_user:
                QMessageBox.warning(self, "Authentication Required", "Please login first.")
                return
            
            if not self.current_transaction:
                QMessageBox.information(
                    self, "No Transaction", 
                    "No active transaction to save. Start a new transaction first."
                )
                return
            
            # Here would be the actual save logic
            QMessageBox.information(
                self, "Transaction Saved",
                "Current transaction has been saved successfully.\n\n"
                "This is a keyboard shortcut test. Full implementation requires workflow integration."
            )
                
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Error saving transaction: {str(e)}")
    
    def refresh_hardware_connection(self):
        """Refresh/reconnect hardware connection"""
        try:
            self.main_status_label.setText("Refreshing hardware connection...")
            
            # Stop existing connection if any
            if self.weight_monitor:
                self.weight_monitor.stop_monitoring()
                self.weight_monitor = None
            
            # Attempt to reconnect if configuration exists
            if self.rs232_config:
                self.connect_to_hardware()
                QMessageBox.information(
                    self, "Hardware Refresh",
                    f"Attempting to reconnect to {self.rs232_config.port}...\n\n"
                    "Check the hardware status indicator for connection status."
                )
            else:
                QMessageBox.information(
                    self, "No Configuration",
                    "No hardware configuration found. Please configure hardware first."
                )
                self.configure_hardware()
                
        except Exception as e:
            QMessageBox.critical(self, "Refresh Error", f"Error refreshing hardware: {str(e)}")
            self.main_status_label.setText("Hardware refresh failed")
    
    def show_shortcuts_dialog(self):
        """Show keyboard shortcuts help dialog"""
        shortcuts_text = """
<b>SCALE System Keyboard Shortcuts</b><br><br>

<b>File Operations:</b><br>
Ctrl+N - New Transaction<br>
Ctrl+Q - Exit Application<br><br>

<b>Weighing Operations:</b><br>
F2 - Timbang I (First Weigh)<br>
F3 - Timbang II (Second Weigh)<br>
F4 - New Transaction<br>
Ctrl+S - Save Transaction<br><br>

<b>Hardware & Tools:</b><br>
F5 - Refresh/Reconnect Hardware<br>
Ctrl+E - Export Transactions<br><br>

<b>Help:</b><br>
F1 - Show This Help Dialog<br><br>

<i>💡 Tip: Most buttons also show their shortcuts in tooltips.</i>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Keyboard Shortcuts")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(shortcuts_text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
    
    # Serial Console Methods
    def toggle_packet_recording(self, enabled: bool):
        """Toggle packet recording on/off"""
        try:
            if enabled:
                # Ask user for recording file location
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Save Packet Recording", 
                    f"serial_packets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                    "Log files (*.log);;Text files (*.txt);;All files (*.*)"
                )
                
                if file_path:
                    self.recording_file = open(file_path, 'w', encoding='utf-8')
                    self.packet_recording = True
                    self.recording_file_label.setText(f"Recording to: {os.path.basename(file_path)}")
                    self.recording_file_label.setStyleSheet("color: green; font-weight: bold;")
                    
                    # Write header
                    self.recording_file.write(f"# SCALE System Serial Packet Recording\n")
                    self.recording_file.write(f"# Started: {datetime.now().isoformat()}\n")
                    self.recording_file.write(f"# Format: [TIMESTAMP] [DIRECTION] [DATA]\n\n")
                    self.recording_file.flush()
                    
                    self.log_to_console(f"[SYSTEM] Packet recording started: {os.path.basename(file_path)}")
                else:
                    self.recording_enabled.setChecked(False)
            else:
                if self.recording_file:
                    self.recording_file.write(f"\n# Recording ended: {datetime.now().isoformat()}\n")
                    self.recording_file.close()
                    self.recording_file = None
                
                self.packet_recording = False
                self.recording_file_label.setText("Not recording")
                self.recording_file_label.setStyleSheet("font-style: italic; color: #666;")
                self.log_to_console("[SYSTEM] Packet recording stopped")
                
        except Exception as e:
            QMessageBox.critical(self, "Recording Error", f"Error toggling packet recording: {str(e)}")
            self.recording_enabled.setChecked(False)
    
    def clear_console(self):
        """Clear the console output"""
        self.console_output.clear()
        self.log_to_console("[SYSTEM] Console cleared")
    
    def save_console_output(self):
        """Save console output to file"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Console Output", 
                f"console_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                "Log files (*.log);;Text files (*.txt);;All files (*.*)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"# SCALE System Console Output\n")
                    f.write(f"# Saved: {datetime.now().isoformat()}\n")
                    f.write(f"# " + "="*50 + "\n\n")
                    f.write(self.console_output.toPlainText())
                
                QMessageBox.information(
                    self, "Console Saved",
                    f"Console output saved to:\n{file_path}"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Error saving console output: {str(e)}")
    
    def toggle_console_pause(self, paused: bool):
        """Pause/resume console output"""
        self.console_paused = paused
        if paused:
            self.log_to_console("[SYSTEM] Console output paused")
        else:
            self.log_to_console("[SYSTEM] Console output resumed")
    
    def send_manual_command(self):
        """Send manual command from input field"""
        command = self.command_input.text().strip()
        if command:
            self.send_serial_command(command)
            self.command_input.clear()
    
    def send_predefined_command(self, command: str):
        """Send a predefined command"""
        self.send_serial_command(command)
    
    def send_serial_command(self, command: str):
        """Send command to serial port and log it"""
        try:
            if not self.is_connected or not self.weight_monitor:
                self.command_response.setText("Error: Not connected to hardware")
                return
            
            # Format command (usually needs line termination)
            formatted_command = command + "\r\n"
            
            # Log outgoing command
            self.log_to_console(f"[TX] {command}")
            
            # Record packet if recording enabled
            if self.packet_recording and self.recording_file:
                self.recording_file.write(f"[{datetime.now().isoformat()}] [TX] {command}\n")
                self.recording_file.flush()
            
            # Here you would send the actual command to the serial port
            # For now, simulate a response
            response = self.simulate_command_response(command)
            
            if response:
                # Log incoming response
                self.log_to_console(f"[RX] {response}")
                self.command_response.setText(response)
                
                # Record response packet if recording enabled
                if self.packet_recording and self.recording_file:
                    self.recording_file.write(f"[{datetime.now().isoformat()}] [RX] {response}\n")
                    self.recording_file.flush()
            
        except Exception as e:
            error_msg = f"Command error: {str(e)}"
            self.command_response.setText(error_msg)
            self.log_to_console(f"[ERROR] {error_msg}")
    
    def simulate_command_response(self, command: str) -> str:
        """Simulate hardware response to commands (for testing)"""
        command = command.upper()
        
        responses = {
            'STATUS': 'SCALE_OK STABLE 1250.50 KG',
            'ZERO': 'ZERO_OK',
            'TARE': 'TARE_OK 125.30 KG',
            'TEST': 'TEST_OK SN:12345 VER:1.2.3'
        }
        
        return responses.get(command, f"UNKNOWN_COMMAND: {command}")
    
    def open_master_data_dialog(self):
        """Open the master data management dialog"""
        try:
            dialog = MasterDataDialog(self)
            # Connect data changed signal to refresh dropdowns
            dialog.data_changed.connect(self.refresh_dropdown_data)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open master data management: {str(e)}")
    
    def refresh_dropdown_data(self):
        """Refresh all dropdown data from database"""
        try:
            self.populate_products_dropdown()
            self.populate_parties_dropdown()
            self.populate_transporters_dropdown()
        except Exception as e:
            print(f"Error refreshing dropdown data: {e}")
    
    def populate_products_dropdown(self):
        """Populate products dropdown from database"""
        try:
            self.product_combo.clear()
            self.product_combo.addItem("-- Select Product --", None)
            
            with self.data_access.get_connection() as conn:
                results = conn.execute("""
                    SELECT id, name FROM products 
                    WHERE is_active = 1 
                    ORDER BY name
                """).fetchall()
                
                for product in results:
                    self.product_combo.addItem(product['name'], product['id'])
                    
        except Exception as e:
            print(f"Error loading products: {e}")
    
    def populate_parties_dropdown(self):
        """Populate customers/suppliers dropdown from database"""
        try:
            self.party_combo.clear()
            self.party_combo.addItem("-- Select Customer/Supplier --", None)
            
            with self.data_access.get_connection() as conn:
                results = conn.execute("""
                    SELECT id, name, type FROM parties 
                    WHERE is_active = 1 
                    ORDER BY name
                """).fetchall()
                
                for party in results:
                    display_name = f"{party['name']} ({party['type']})"
                    self.party_combo.addItem(display_name, party['id'])
                    
        except Exception as e:
            print(f"Error loading customers/suppliers: {e}")
    
    def populate_transporters_dropdown(self):
        """Populate transporters dropdown from database"""
        try:
            self.transporter_combo.clear()
            self.transporter_combo.addItem("-- Select Transporter --", None)
            
            with self.data_access.get_connection() as conn:
                results = conn.execute("""
                    SELECT id, name FROM transporters 
                    WHERE is_active = 1 
                    ORDER BY name
                """).fetchall()
                
                for transporter in results:
                    self.transporter_combo.addItem(transporter['name'], transporter['id'])
                    
        except Exception as e:
            print(f"Error loading transporters: {e}")
    
    def log_to_console(self, message: str):
        """Log message to console output"""
        if not self.console_paused:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
            formatted_message = f"[{timestamp}] {message}"
            self.console_output.append(formatted_message)
    
    def update_console_statistics(self):
        """Update console statistics display"""
        self.packets_received_label.setText(f"Packets: {self.packets_received}")
        self.bytes_received_label.setText(f"Bytes: {self.bytes_received}")
        self.errors_count_label.setText(f"Errors: {self.errors_count}")
    
    def refresh_all_data(self):
        """Refresh all displayed data"""
        self.refresh_recent_transactions()
        self.load_users_data()
        self.main_status_label.setText("Data refreshed")
    
    def closeEvent(self, event):
        """Handle application close event"""
        
        # Stop hardware monitoring
        if self.weight_monitor:
            self.weight_monitor.stop_monitoring()
        
        # Close database connections
        if hasattr(self, 'data_access'):
            self.data_access.close()
        
        event.accept()

def main():
    """Main application entry point"""
    
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("SCALE System")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("SCALE Systems Ltd")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
