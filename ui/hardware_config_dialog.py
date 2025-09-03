#!/usr/bin/env python3
"""
SCALE System Enhanced Hardware Configuration Dialog
Automatic RS232 port detection with manual selection capabilities
"""

import sys
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QGroupBox,
    QProgressBar, QTextEdit, QCheckBox, QSpinBox,
    QTabWidget, QWidget, QFrame, QSplitter,
    QMessageBox, QApplication, QLineEdit
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer,
    QSize, QRect, pyqtSlot
)
from PyQt6.QtGui import (
    QFont, QIcon, QPalette, QColor, QPixmap,
    QPainter, QBrush, QPen
)

# Import SCALE system components
sys.path.append('..')
from hardware.rs232_manager import RS232Manager, RS232Config, RS232Status
from hardware.hardware_config import HardwareProfileManager, SerialProfile
from utils.helpers import format_timestamp

class PortScanWorker(QThread):
    """Background thread for scanning RS232 ports"""
    
    scan_completed = pyqtSignal(list)  # List of port dictionaries
    scan_progress = pyqtSignal(int)    # Progress percentage
    scan_status = pyqtSignal(str)      # Status message
    
    def __init__(self):
        super().__init__()
        self.rs232_manager = RS232Manager()
        self.is_scanning = False
    
    def run(self):
        """Perform port scanning in background thread"""
        self.is_scanning = True
        self.scan_status.emit("Scanning for RS232 ports...")
        self.scan_progress.emit(10)
        
        try:
            # Get available ports
            ports = self.rs232_manager.get_available_ports()
            self.scan_progress.emit(50)
            
            # Test each port with basic communication
            enhanced_ports = []
            total_ports = len(ports) if ports else 1
            
            for i, port in enumerate(ports):
                self.scan_status.emit(f"Testing {port['device']}...")
                
                # Quick connectivity test
                port_info = port.copy()
                port_info['test_result'] = self._test_port_connectivity(port['device'])
                enhanced_ports.append(port_info)
                
                progress = 50 + int((i + 1) / total_ports * 40)
                self.scan_progress.emit(progress)
            
            self.scan_progress.emit(100)
            self.scan_status.emit(f"Found {len(enhanced_ports)} port(s)")
            self.scan_completed.emit(enhanced_ports)
            
        except Exception as e:
            self.scan_status.emit(f"Scan error: {str(e)}")
            self.scan_completed.emit([])
        
        finally:
            self.is_scanning = False
    
    def _test_port_connectivity(self, port_device: str) -> Dict:
        """Test basic connectivity on a port"""
        
        try:
            # Quick test with default 9600 baud
            config = RS232Config(port=port_device, baud_rate=9600, timeout=0.5)
            result = self.rs232_manager.test_connection(config, "TEST\r\n")
            
            return {
                'accessible': result.success,
                'response_time': result.response_time,
                'error': result.error_message
            }
            
        except Exception as e:
            return {
                'accessible': False,
                'response_time': 0,
                'error': str(e)
            }

class ConnectionTestWorker(QThread):
    """Background thread for testing port connections"""
    
    test_completed = pyqtSignal(dict)  # Test results
    test_progress = pyqtSignal(int, str)  # Progress and status
    
    def __init__(self, port: str, baud_rates: List[int]):
        super().__init__()
        self.port = port
        self.baud_rates = baud_rates
        self.rs232_manager = RS232Manager()
    
    def run(self):
        """Test connection with multiple baud rates"""
        
        results = {
            'port': self.port,
            'tests': [],
            'best_baud_rate': None,
            'overall_success': False
        }
        
        total_tests = len(self.baud_rates)
        
        for i, baud_rate in enumerate(self.baud_rates):
            self.test_progress.emit(
                int((i / total_tests) * 100),
                f"Testing {baud_rate} baud..."
            )
            
            config = RS232Config(port=self.port, baud_rate=baud_rate, timeout=2.0)
            result = self.rs232_manager.test_connection(config, "SCALE_TEST\r\n")
            
            test_result = {
                'baud_rate': baud_rate,
                'success': result.success,
                'response_time': result.response_time,
                'bytes_received': result.bytes_received,
                'error': result.error_message
            }
            
            results['tests'].append(test_result)
            
            # Track best performing baud rate
            if result.success and result.bytes_received > 0:
                if results['best_baud_rate'] is None:
                    results['best_baud_rate'] = baud_rate
                results['overall_success'] = True
        
        self.test_progress.emit(100, "Test completed")
        self.test_completed.emit(results)

class HardwareConfigDialog(QDialog):
    """Enhanced Hardware Configuration Dialog with automated port detection"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile_manager = HardwareProfileManager()
        self.rs232_manager = RS232Manager()
        self.current_ports = []
        self.selected_profile = None
        
        # Threads for background operations
        self.scan_worker = None
        self.test_worker = None
        
        self.setup_ui()
        self.setup_timers()
        self.start_initial_scan()
    
    def setup_ui(self):
        """Setup the user interface"""
        
        self.setWindowTitle("Hardware Configuration - SCALE System")
        self.setFixedSize(800, 600)
        self.setModal(True)
        
        # Apply modern styling
        self.setStyleSheet("""
            QDialog {
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
            QComboBox {
                padding: 6px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit {
                padding: 6px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
            }
            QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Hardware Configuration")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Port Detection Tab
        self.port_tab = self.create_port_detection_tab()
        self.tab_widget.addTab(self.port_tab, "🔍 Port Detection")
        
        # Manual Configuration Tab  
        self.config_tab = self.create_manual_config_tab()
        self.tab_widget.addTab(self.config_tab, "⚙️ Manual Config")
        
        # Profile Management Tab
        self.profile_tab = self.create_profile_management_tab()
        self.tab_widget.addTab(self.profile_tab, "📋 Profiles")
        
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        self.status_layout.addWidget(self.status_label)
        self.status_layout.addWidget(self.progress_bar)
        main_layout.addLayout(self.status_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.test_connection_btn = QPushButton("🧪 Test Connection")
        self.test_connection_btn.clicked.connect(self.test_selected_connection)
        
        self.apply_btn = QPushButton("✅ Apply Configuration")
        self.apply_btn.clicked.connect(self.apply_configuration)
        
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.test_connection_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def create_port_detection_tab(self) -> QWidget:
        """Create the automated port detection tab"""
        
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Auto-detection group
        auto_group = QGroupBox("Automatic Port Detection")
        auto_layout = QVBoxLayout()
        
        # Scan controls
        scan_layout = QHBoxLayout()
        self.auto_scan_btn = QPushButton("🔄 Scan Ports")
        self.auto_scan_btn.clicked.connect(self.start_port_scan)
        
        self.auto_refresh_check = QCheckBox("Auto-refresh every 10 seconds")
        self.auto_refresh_check.stateChanged.connect(self.toggle_auto_refresh)
        
        scan_layout.addWidget(self.auto_scan_btn)
        scan_layout.addWidget(self.auto_refresh_check)
        scan_layout.addStretch()
        
        auto_layout.addLayout(scan_layout)
        
        # Detected ports list
        ports_layout = QGridLayout()
        ports_layout.addWidget(QLabel("Detected Port:"), 0, 0)
        
        self.port_combo = QComboBox()
        self.port_combo.currentTextChanged.connect(self.on_port_selection_changed)
        ports_layout.addWidget(self.port_combo, 0, 1, 1, 2)
        
        ports_layout.addWidget(QLabel("Port Status:"), 1, 0)
        self.port_status_label = QLabel("No port selected")
        ports_layout.addWidget(self.port_status_label, 1, 1, 1, 2)
        
        ports_layout.addWidget(QLabel("Port Info:"), 2, 0)
        self.port_info_text = QTextEdit()
        self.port_info_text.setMaximumHeight(100)
        self.port_info_text.setReadOnly(True)
        ports_layout.addWidget(self.port_info_text, 2, 1, 1, 2)
        
        auto_layout.addLayout(ports_layout)
        auto_group.setLayout(auto_layout)
        layout.addWidget(auto_group)
        
        # Baud rate detection group
        baud_group = QGroupBox("Baud Rate Configuration")
        baud_layout = QGridLayout()
        
        baud_layout.addWidget(QLabel("Baud Rate:"), 0, 0)
        
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "115200"])
        self.baud_combo.setCurrentText("9600")
        baud_layout.addWidget(self.baud_combo, 0, 1)
        
        self.auto_detect_baud_btn = QPushButton("🎯 Auto-detect Baud Rate")
        self.auto_detect_baud_btn.clicked.connect(self.auto_detect_baud_rate)
        baud_layout.addWidget(self.auto_detect_baud_btn, 0, 2)
        
        # Advanced settings
        baud_layout.addWidget(QLabel("Data Bits:"), 1, 0)
        self.data_bits_combo = QComboBox()
        self.data_bits_combo.addItems(["7", "8"])
        self.data_bits_combo.setCurrentText("8")
        baud_layout.addWidget(self.data_bits_combo, 1, 1)
        
        baud_layout.addWidget(QLabel("Parity:"), 2, 0)
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None (N)", "Even (E)", "Odd (O)"])
        baud_layout.addWidget(self.parity_combo, 2, 1)
        
        baud_layout.addWidget(QLabel("Stop Bits:"), 3, 0)
        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItems(["1", "2"])
        baud_layout.addWidget(self.stop_bits_combo, 3, 1)
        
        baud_group.setLayout(baud_layout)
        layout.addWidget(baud_group)
        
        # Test results group
        test_group = QGroupBox("Connection Test Results")
        test_layout = QVBoxLayout()
        
        self.test_results_text = QTextEdit()
        self.test_results_text.setMaximumHeight(120)
        self.test_results_text.setReadOnly(True)
        self.test_results_text.setPlainText("No tests performed yet. Click 'Test Connection' to validate settings.")
        
        test_layout.addWidget(self.test_results_text)
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        
        tab.setLayout(layout)
        return tab
    
    def create_manual_config_tab(self) -> QWidget:
        """Create manual configuration tab"""
        
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Manual port entry group
        manual_group = QGroupBox("Manual Port Configuration")
        manual_layout = QGridLayout()
        
        manual_layout.addWidget(QLabel("Port Path:"), 0, 0)
        self.manual_port_edit = QLineEdit()
        self.manual_port_edit.setPlaceholderText("e.g., COM1, /dev/ttyUSB0")
        manual_layout.addWidget(self.manual_port_edit, 0, 1)
        
        self.browse_port_btn = QPushButton("Browse...")
        self.browse_port_btn.clicked.connect(self.browse_for_port)
        manual_layout.addWidget(self.browse_port_btn, 0, 2)
        
        manual_group.setLayout(manual_layout)
        layout.addWidget(manual_group)
        
        # Advanced settings group
        advanced_group = QGroupBox("Advanced RS232 Settings")
        advanced_layout = QGridLayout()
        
        # Timeout settings
        advanced_layout.addWidget(QLabel("Read Timeout (s):"), 0, 0)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 10)
        self.timeout_spin.setValue(2)
        advanced_layout.addWidget(self.timeout_spin, 0, 1)
        
        # Flow control
        advanced_layout.addWidget(QLabel("Flow Control:"), 1, 0)
        self.flow_control_combo = QComboBox()
        self.flow_control_combo.addItems(["None", "XON/XOFF", "RTS/CTS", "DSR/DTR"])
        advanced_layout.addWidget(self.flow_control_combo, 1, 1)
        
        # Hardware control lines
        advanced_layout.addWidget(QLabel("Hardware Control:"), 2, 0)
        
        hw_control_layout = QHBoxLayout()
        self.dtr_check = QCheckBox("DTR")
        self.dtr_check.setChecked(True)
        self.rts_check = QCheckBox("RTS") 
        self.rts_check.setChecked(True)
        
        hw_control_layout.addWidget(self.dtr_check)
        hw_control_layout.addWidget(self.rts_check)
        hw_control_layout.addStretch()
        
        advanced_layout.addLayout(hw_control_layout, 2, 1)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def create_profile_management_tab(self) -> QWidget:
        """Create profile management tab"""
        
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Profile selection group
        profile_group = QGroupBox("Hardware Profiles")
        profile_layout = QGridLayout()
        
        profile_layout.addWidget(QLabel("Select Profile:"), 0, 0)
        
        self.profile_combo = QComboBox()
        self.load_profiles()
        self.profile_combo.currentTextChanged.connect(self.on_profile_selection_changed)
        profile_layout.addWidget(self.profile_combo, 0, 1)
        
        self.load_profile_btn = QPushButton("📁 Load Profile")
        self.load_profile_btn.clicked.connect(self.load_selected_profile)
        profile_layout.addWidget(self.load_profile_btn, 0, 2)
        
        # Profile details
        profile_layout.addWidget(QLabel("Profile Details:"), 1, 0)
        self.profile_details_text = QTextEdit()
        self.profile_details_text.setMaximumHeight(120)
        self.profile_details_text.setReadOnly(True)
        profile_layout.addWidget(self.profile_details_text, 1, 1, 1, 2)
        
        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)
        
        # Profile management buttons
        profile_btn_layout = QHBoxLayout()
        
        self.save_profile_btn = QPushButton("💾 Save As New Profile")
        self.save_profile_btn.clicked.connect(self.save_current_as_profile)
        
        self.delete_profile_btn = QPushButton("🗑️ Delete Profile")
        self.delete_profile_btn.clicked.connect(self.delete_selected_profile)
        
        profile_btn_layout.addWidget(self.save_profile_btn)
        profile_btn_layout.addWidget(self.delete_profile_btn)
        profile_btn_layout.addStretch()
        
        layout.addLayout(profile_btn_layout)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def setup_timers(self):
        """Setup auto-refresh timer"""
        
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.start_port_scan)
        self.auto_refresh_timer.setInterval(10000)  # 10 seconds
    
    def start_initial_scan(self):
        """Start initial port scan when dialog opens"""
        
        self.start_port_scan()
    
    @pyqtSlot()
    def start_port_scan(self):
        """Start scanning for ports in background thread"""
        
        if self.scan_worker and self.scan_worker.is_scanning:
            return  # Already scanning
        
        self.auto_scan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.scan_worker = PortScanWorker()
        self.scan_worker.scan_completed.connect(self.on_scan_completed)
        self.scan_worker.scan_progress.connect(self.progress_bar.setValue)
        self.scan_worker.scan_status.connect(self.status_label.setText)
        self.scan_worker.start()
    
    @pyqtSlot(list)
    def on_scan_completed(self, ports: List[Dict]):
        """Handle completion of port scan"""
        
        self.current_ports = ports
        self.auto_scan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Update port combo box
        self.port_combo.clear()
        
        if not ports:
            self.port_combo.addItem("No ports detected")
            self.port_status_label.setText("❌ No RS232 ports found")
            self.port_info_text.setPlainText("No serial ports detected on this system.")
        else:
            for port in ports:
                display_name = f"{port['device']} - {port['description']}"
                self.port_combo.addItem(display_name, port)
            
            # Auto-select first working port
            self.select_best_port()
        
        self.status_label.setText(f"Found {len(ports)} port(s)")
    
    def select_best_port(self):
        """Auto-select the best available port"""
        
        if not self.current_ports:
            return
        
        # Look for a port that tested successfully
        for i, port in enumerate(self.current_ports):
            if port.get('test_result', {}).get('accessible', False):
                self.port_combo.setCurrentIndex(i)
                return
        
        # Otherwise select the first port
        self.port_combo.setCurrentIndex(0)
    
    @pyqtSlot(str)
    def on_port_selection_changed(self, selected_text: str):
        """Handle port selection change"""
        
        if not self.current_ports or selected_text == "No ports detected":
            self.port_status_label.setText("No port selected")
            self.port_info_text.clear()
            return
        
        # Get selected port data
        current_index = self.port_combo.currentIndex()
        if current_index < 0 or current_index >= len(self.current_ports):
            return
        
        port = self.current_ports[current_index]
        test_result = port.get('test_result', {})
        
        # Update status
        if test_result.get('accessible', False):
            self.port_status_label.setText("✅ Port accessible")
        else:
            self.port_status_label.setText("⚠️ Port may not be accessible")
        
        # Update info display
        info_text = f"""Port: {port['device']}
Name: {port['name']}
Description: {port['description']}
Manufacturer: {port['manufacturer']}
Serial Number: {port.get('serial_number', 'Unknown')}
Hardware ID: {port['vid']}:{port['pid']}

Test Result:
- Accessible: {'Yes' if test_result.get('accessible') else 'No'}
- Response Time: {test_result.get('response_time', 0):.3f}s
Error: {test_result.get('error', 'None')}"""
        
        self.port_info_text.setPlainText(info_text)
        
        # Auto-populate manual port field
        self.manual_port_edit.setText(port['device'])
    
    @pyqtSlot()
    def auto_detect_baud_rate(self):
        """Auto-detect optimal baud rate for selected port"""
        
        selected_port = self.get_selected_port_device()
        if not selected_port:
            QMessageBox.warning(self, "No Port Selected", 
                              "Please select a port first.")
            return
        
        # Test with all supported baud rates
        baud_rates = [9600, 19200, 38400, 115200]
        
        self.auto_detect_baud_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        
        self.test_worker = ConnectionTestWorker(selected_port, baud_rates)
        self.test_worker.test_completed.connect(self.on_baud_detection_completed)
        self.test_worker.test_progress.connect(self.on_test_progress)
        self.test_worker.start()
    
    @pyqtSlot(int, str)
    def on_test_progress(self, progress: int, status: str):
        """Handle test progress updates"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)
    
    @pyqtSlot(dict)
    def on_baud_detection_completed(self, results: Dict):
        """Handle baud rate detection completion"""
        
        self.auto_detect_baud_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if results['best_baud_rate']:
            self.baud_combo.setCurrentText(str(results['best_baud_rate']))
            self.status_label.setText(f"✅ Detected optimal baud rate: {results['best_baud_rate']}")
        else:
            self.status_label.setText("⚠️ Could not detect optimal baud rate")
        
        # Display detailed results
        results_text = f"Baud Rate Detection Results for {results['port']}:\n\n"
        
        for test in results['tests']:
            status_icon = "✅" if test['success'] else "❌"
            results_text += f"{status_icon} {test['baud_rate']} baud: "
            
            if test['success']:
                results_text += f"OK ({test['response_time']:.3f}s, {test['bytes_received']} bytes)\n"
            else:
                results_text += f"Failed - {test['error']}\n"
        
        if results['best_baud_rate']:
            results_text += f"\n🎯 Recommended: {results['best_baud_rate']} baud"
        
        self.test_results_text.setPlainText(results_text)
    
    @pyqtSlot()
    def test_selected_connection(self):
        """Test the currently selected connection configuration"""
        
        config = self.get_current_config()
        if not config:
            QMessageBox.warning(self, "Invalid Configuration",
                              "Please configure a valid port and settings.")
            return
        
        self.test_connection_btn.setEnabled(False)
        self.status_label.setText("Testing connection...")
        
        try:
            result = self.rs232_manager.test_connection(config, "SCALE_TEST\r\n")
            
            if result.success:
                status = f"✅ Connection successful ({result.response_time:.3f}s)"
                if result.bytes_received > 0:
                    status += f" - Received {result.bytes_received} bytes"
                
                self.test_results_text.setPlainText(
                    f"Connection Test Results:\n\n"
                    f"Port: {config.port}\n"
                    f"Baud Rate: {config.baud_rate}\n"
                    f"Status: SUCCESS\n"
                    f"Response Time: {result.response_time:.3f}s\n"
                    f"Bytes Received: {result.bytes_received}\n"
                    f"Raw Response: {repr(result.raw_response)}\n\n"
                    f"✅ Configuration is working correctly!"
                )
            else:
                status = f"❌ Connection failed: {result.error_message}"
                self.test_results_text.setPlainText(
                    f"Connection Test Results:\n\n"
                    f"Port: {config.port}\n"
                    f"Baud Rate: {config.baud_rate}\n"
                    f"Status: FAILED\n"
                    f"Error: {result.error_message}\n\n"
                    f"❌ Please check your configuration and hardware."
                )
            
            self.status_label.setText(status)
            
        except Exception as e:
            error_msg = f"Test error: {str(e)}"
            self.status_label.setText(f"❌ {error_msg}")
            self.test_results_text.setPlainText(f"Connection test failed:\n{error_msg}")
        
        finally:
            self.test_connection_btn.setEnabled(True)
    
    def get_selected_port_device(self) -> Optional[str]:
        """Get the currently selected port device name"""
        
        # Check manual entry first
        manual_port = self.manual_port_edit.text().strip()
        if manual_port:
            return manual_port
        
        # Check auto-detected port
        if self.current_ports and self.port_combo.currentIndex() >= 0:
            current_index = self.port_combo.currentIndex()
            if current_index < len(self.current_ports):
                return self.current_ports[current_index]['device']
        
        return None
    
    def get_current_config(self) -> Optional[RS232Config]:
        """Get current RS232 configuration"""
        
        port = self.get_selected_port_device()
        if not port:
            return None
        
        # Parse parity setting
        parity_text = self.parity_combo.currentText()
        parity = 'N'
        if 'Even' in parity_text:
            parity = 'E'
        elif 'Odd' in parity_text:
            parity = 'O'
        
        # Parse flow control
        flow_control = 'none'
        flow_text = self.flow_control_combo.currentText().lower()
        if 'xon' in flow_text:
            flow_control = 'xon_xoff'
        elif 'rts' in flow_text:
            flow_control = 'rts_cts'
        elif 'dsr' in flow_text:
            flow_control = 'dsr_dtr'
        
        return RS232Config(
            port=port,
            baud_rate=int(self.baud_combo.currentText()),
            data_bits=int(self.data_bits_combo.currentText()),
            parity=parity,
            stop_bits=int(self.stop_bits_combo.currentText()),
            flow_control=flow_control,
            timeout=float(self.timeout_spin.value()),
            dtr=self.dtr_check.isChecked(),
            rts=self.rts_check.isChecked()
        )
    
    @pyqtSlot()
    def toggle_auto_refresh(self):
        """Toggle auto-refresh timer"""
        
        if self.auto_refresh_check.isChecked():
            self.auto_refresh_timer.start()
            self.status_label.setText("Auto-refresh enabled")
        else:
            self.auto_refresh_timer.stop()
            self.status_label.setText("Auto-refresh disabled")
    
    def load_profiles(self):
        """Load available hardware profiles"""
        
        profiles = self.profile_manager.get_all_profiles()
        self.profile_combo.clear()
        
        for name in profiles.keys():
            self.profile_combo.addItem(name)
    
    @pyqtSlot(str)
    def on_profile_selection_changed(self, profile_name: str):
        """Handle profile selection change"""
        
        if not profile_name:
            return
        
        try:
            profile = self.profile_manager.get_profile(profile_name)
            
            # Display profile details
            details = f"""Profile: {profile.name}
Port: {profile.port}
Baud Rate: {profile.baud_rate}
Data Format: {profile.data_bits}-{profile.parity}-{profile.stop_bits}
Timeout: {profile.timeout}s
Protocol: {profile.protocol}
Stable Indicator: '{profile.stable_indicator}'
Weight Pattern: {profile.weight_pattern}"""
            
            self.profile_details_text.setPlainText(details)
            
        except Exception as e:
            self.profile_details_text.setPlainText(f"Error loading profile: {e}")
    
    @pyqtSlot()
    def load_selected_profile(self):
        """Load selected profile into current configuration"""
        
        profile_name = self.profile_combo.currentText()
        if not profile_name:
            return
        
        try:
            profile = self.profile_manager.get_profile(profile_name)
            
            # Apply profile settings to UI
            self.manual_port_edit.setText(profile.port)
            self.baud_combo.setCurrentText(str(profile.baud_rate))
            self.data_bits_combo.setCurrentText(str(profile.data_bits))
            
            # Set parity
            parity_map = {'N': 'None (N)', 'E': 'Even (E)', 'O': 'Odd (O)'}
            self.parity_combo.setCurrentText(parity_map.get(profile.parity, 'None (N)'))
            
            self.stop_bits_combo.setCurrentText(str(profile.stop_bits))
            self.timeout_spin.setValue(int(profile.timeout))
            
            self.selected_profile = profile
            self.status_label.setText(f"✅ Loaded profile: {profile.name}")
            
            QMessageBox.information(self, "Profile Loaded",
                                  f"Profile '{profile.name}' has been loaded successfully.")
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error",
                               f"Failed to load profile: {str(e)}")
    
    @pyqtSlot()
    def save_current_as_profile(self):
        """Save current configuration as a new profile"""
        
        # Implementation for profile saving
        # This would open a dialog to enter profile name and save current settings
        QMessageBox.information(self, "Feature Not Implemented",
                              "Profile saving will be implemented in the next update.")
    
    @pyqtSlot()
    def delete_selected_profile(self):
        """Delete the selected profile"""
        
        profile_name = self.profile_combo.currentText()
        if not profile_name:
            return
        
        reply = QMessageBox.question(
            self, "Delete Profile",
            f"Are you sure you want to delete the profile '{profile_name}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.profile_manager.delete_profile(profile_name)
                if success:
                    self.load_profiles()  # Refresh the combo box
                    self.status_label.setText(f"✅ Deleted profile: {profile_name}")
                    QMessageBox.information(self, "Profile Deleted",
                                          f"Profile '{profile_name}' has been deleted.")
                else:
                    QMessageBox.warning(self, "Delete Failed",
                                       f"Could not delete profile '{profile_name}'.")
            except Exception as e:
                QMessageBox.critical(self, "Delete Error",
                                   f"Failed to delete profile: {str(e)}")
    
    @pyqtSlot()
    def browse_for_port(self):
        """Browse for port (placeholder for file dialog)"""
        
        # On Linux, this could open a file dialog to browse /dev/
        # On Windows, show available COM ports
        QMessageBox.information(self, "Manual Port Entry",
                              "Enter the port path manually:\n\n"
                              "Windows: COM1, COM2, COM3, etc.\n"
                              "Linux: /dev/ttyUSB0, /dev/ttyS0, etc.")
    
    @pyqtSlot()
    def apply_configuration(self):
        """Apply the current configuration and close dialog"""
        
        config = self.get_current_config()
        if not config:
            QMessageBox.warning(self, "Invalid Configuration",
                              "Please configure a valid port and settings before applying.")
            return
        
        # Store the configuration for parent window
        self.final_config = config
        self.accept()
    
    def get_final_configuration(self) -> Optional[RS232Config]:
        """Get the final configuration after dialog closes"""
        return getattr(self, 'final_config', None)

# Demo application to test the dialog
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    dialog = HardwareConfigDialog()
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        config = dialog.get_final_configuration()
        if config:
            print(f"Configuration accepted:")
            print(f"  Port: {config.port}")
            print(f"  Baud Rate: {config.baud_rate}")
            print(f"  Data Format: {config.data_bits}-{config.parity}-{config.stop_bits}")
            print(f"  Timeout: {config.timeout}s")
    else:
        print("Configuration cancelled")
    
    sys.exit(0)
