#!/usr/bin/env python3
"""
SCALE System Core Module
Main application configuration and constants
"""

import os
from pathlib import Path
from typing import Dict, Any

# Application Information
APP_NAME = "SCALE System"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Professional Weighbridge Management System"
APP_AUTHOR = "MiniMax Agent"

# File Paths
APP_DIR = Path(__file__).parent.parent
DATA_DIR = APP_DIR / "data"
CONFIG_DIR = APP_DIR / "config"
LOGS_DIR = APP_DIR / "logs"
BACKUP_DIR = APP_DIR / "backups"
REPORTS_DIR = APP_DIR / "reports"
TEMPLATES_DIR = APP_DIR / "templates"

# Ensure directories exist
for directory in [DATA_DIR, CONFIG_DIR, LOGS_DIR, BACKUP_DIR, REPORTS_DIR, TEMPLATES_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_PATH = DATA_DIR / "scale_system.db"
BACKUP_DATABASE_PATH = BACKUP_DIR / "scale_system_backup.db"

# Configuration Files
HARDWARE_PROFILES_FILE = CONFIG_DIR / "hardware_profiles.json"
APP_CONFIG_FILE = CONFIG_DIR / "app_config.json"
USER_PREFERENCES_FILE = CONFIG_DIR / "user_preferences.json"

# Logging
APP_LOG_FILE = LOGS_DIR / "scale_system.log"
SERIAL_LOG_FILE = LOGS_DIR / "serial_communication.log"
AUDIT_LOG_FILE = LOGS_DIR / "audit_trail.log"

# Application Modes
class ApplicationMode:
    LIVE = "LIVE"
    TEST = "TEST"
    DEMO = "DEMO"

# User Roles
class UserRole:
    OPERATOR = "Operator"
    SUPERVISOR = "Supervisor"
    ADMIN = "Admin"

# Transaction Status
class TransactionStatus:
    PENDING = "pending"
    COMPLETE = "complete"
    VOID = "void"

# Transaction Modes
class TransactionMode:
    TWO_PASS = "two_pass"
    FIXED_TARE = "fixed_tare"

# Weight Units
class WeightUnit:
    KG = "KG"
    LB = "LB"
    G = "G"
    TON = "TON"

# Default Settings
DEFAULT_SETTINGS = {
    # Application Mode
    'application_mode': ApplicationMode.LIVE,  # LIVE, TEST, or DEMO
    'test_mode_enabled': False,
    'simulation_enabled': False,
    'mock_hardware': False,
    
    # Serial Communication
    'serial_port': 'COM1',
    'serial_baud_rate': 9600,
    'serial_data_bits': 8,
    'serial_parity': 'N',
    'serial_stop_bits': 1,
    'serial_timeout': 1.0,
    'serial_protocol': 'generic',
    
    # Weight Settings
    'weight_decimal_places': 2,
    'weight_rounding_mode': 'round_half_up',
    'weight_unit': WeightUnit.KG,
    'stable_weight_threshold': 0.5,
    'stable_weight_duration': 3,
    
    # Ticket Settings
    'ticket_prefix': 'SC',
    'ticket_sequence_reset': 'yearly',
    'ticket_number_padding': 6,
    
    # Application Settings
    'application_mode': ApplicationMode.LIVE,
    'stale_pending_hours': 24,
    'auto_backup_enabled': True,
    'backup_retention_days': 30,
    'auto_vacuum_enabled': True,
    'vacuum_interval_hours': 24,
    
    # UI Settings
    'locale': 'en_US',
    'date_format': '%Y-%m-%d',
    'time_format': '%H:%M:%S',
    'datetime_format': '%Y-%m-%d %H:%M:%S',
    'theme': 'default',
    'font_size': 12,
    
    # Printing Settings
    'default_printer_type': 'A4',
    'auto_print_tickets': True,
    'print_copies': 1,
    
    # Security Settings
    'session_timeout_minutes': 480,  # 8 hours
    'require_pin_for_void': True,
    'require_reason_for_void': True,
    'audit_level': 'detailed',
    
    # Diagnostic Settings
    'enable_packet_recording': False,
    'max_console_lines': 1000,
    'log_level': 'INFO',
    'max_log_size_mb': 10,
    'log_rotation_count': 5
}

# Keyboard Shortcuts
KEYBOARD_SHORTCUTS = {
    'F1': 'help',
    'F2': 'weigh_1',
    'F3': 'weigh_2',
    'F4': 'complete_transaction',
    'F5': 'new_transaction',
    'F6': 'void_transaction',
    'F7': 'reports',
    'F8': 'settings',
    'F9': 'diagnostics',
    'F10': 'exit',
    'Ctrl+S': 'save',
    'Ctrl+P': 'print',
    'Ctrl+B': 'backup',
    'Ctrl+R': 'refresh',
    'Ctrl+F': 'find',
    'Ctrl+N': 'new',
    'Ctrl+Q': 'quit',
    'Escape': 'cancel'
}

# Validation Rules
VALIDATION_RULES = {
    'vehicle_no': {
        'max_length': 20,
        'pattern': r'^[A-Z0-9-]+$',
        'required': True
    },
    'ticket_no': {
        'min_value': 1,
        'max_value': 999999999,
        'required': True
    },
    'weight': {
        'min_value': 0.0,
        'max_value': 999999.99,
        'decimal_places': 2
    },
    'notes': {
        'max_length': 500
    },
    'do_po_no': {
        'max_length': 50
    },
    'username': {
        'min_length': 3,
        'max_length': 20,
        'pattern': r'^[a-zA-Z0-9_]+$',
        'required': True
    },
    'pin': {
        'min_length': 4,
        'max_length': 6,
        'pattern': r'^\d+$'
    }
}

# Error Messages
ERROR_MESSAGES = {
    'database_connection': 'Failed to connect to database',
    'serial_connection': 'Failed to connect to weight indicator',
    'invalid_weight': 'Invalid weight reading',
    'unstable_weight': 'Weight is not stable',
    'transaction_exists': 'Vehicle already has pending transaction',
    'transaction_not_found': 'Transaction not found',
    'invalid_user': 'Invalid username or PIN',
    'access_denied': 'Access denied for this operation',
    'validation_failed': 'Input validation failed',
    'backup_failed': 'Database backup failed',
    'restore_failed': 'Database restore failed'
}

# Success Messages
SUCCESS_MESSAGES = {
    'transaction_created': 'Transaction created successfully',
    'transaction_completed': 'Transaction completed successfully',
    'transaction_voided': 'Transaction voided successfully',
    'weight_captured': 'Weight captured successfully',
    'backup_created': 'Database backup created successfully',
    'settings_updated': 'Settings updated successfully',
    'user_authenticated': 'User authenticated successfully',
    'data_exported': 'Data exported successfully'
}

# Report Types
REPORT_TYPES = {
    'daily_summary': {
        'name': 'Daily Summary',
        'description': 'Summary of transactions for selected date',
        'template': 'daily_summary.html'
    },
    'vehicle_history': {
        'name': 'Vehicle History',
        'description': 'Transaction history for specific vehicle',
        'template': 'vehicle_history.html'
    },
    'product_summary': {
        'name': 'Product Summary',
        'description': 'Summary by product for date range',
        'template': 'product_summary.html'
    },
    'party_summary': {
        'name': 'Party Summary',
        'description': 'Summary by customer/supplier',
        'template': 'party_summary.html'
    },
    'exception_report': {
        'name': 'Exception Report',
        'description': 'Void transactions and manual overrides',
        'template': 'exception_report.html'
    },
    'audit_trail': {
        'name': 'Audit Trail',
        'description': 'Detailed audit log for date range',
        'template': 'audit_trail.html'
    }
}

# Export Formats
EXPORT_FORMATS = {
    'csv': 'Comma Separated Values',
    'pdf': 'Portable Document Format',
    'excel': 'Microsoft Excel Worksheet',
    'json': 'JavaScript Object Notation'
}

# Application Status
class AppStatus:
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

def get_app_info() -> Dict[str, Any]:
    """Get application information"""
    return {
        'name': APP_NAME,
        'version': APP_VERSION,
        'description': APP_DESCRIPTION,
        'author': APP_AUTHOR,
        'app_dir': str(APP_DIR),
        'data_dir': str(DATA_DIR),
        'config_dir': str(CONFIG_DIR),
        'database_path': str(DATABASE_PATH)
    }

def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    import platform
    import sys
    
    return {
        'platform': platform.platform(),
        'system': platform.system(),
        'processor': platform.processor(),
        'python_version': sys.version,
        'python_executable': sys.executable
    }
