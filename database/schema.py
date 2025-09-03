#!/usr/bin/env python3
"""
SCALE System Database Schema
Implements the complete SQLite database schema with WAL mode and proper constraints
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

class DatabaseSchema:
    """Handles database schema creation and initialization"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def initialize_database(self) -> None:
        """Initialize the database with all tables and configurations"""
        with sqlite3.connect(self.db_path) as conn:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=1000")
            conn.execute("PRAGMA temp_store=MEMORY")
            
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys=ON")
            
            self._create_tables(conn)
            self._create_indexes(conn)
            self._insert_default_data(conn)
            
            conn.commit()
    
    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create all database tables"""
        
        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                pin_hash TEXT,
                role TEXT NOT NULL CHECK (role IN ('Operator', 'Supervisor', 'Admin')),
                created_at_utc TEXT NOT NULL,
                created_by TEXT,
                active INTEGER DEFAULT 1
            )
        """)
        
        # Settings table (key-value store)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                data_type TEXT DEFAULT 'string',
                description TEXT,
                updated_at_utc TEXT NOT NULL,
                updated_by TEXT,
                FOREIGN KEY (updated_by) REFERENCES users(id)
            )
        """)
        
        # Vehicles table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_no TEXT PRIMARY KEY,
                fixed_tare REAL,
                driver_name TEXT,
                notes TEXT,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL
            )
        """)
        
        # Printers table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS printers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT CHECK (type IN ('A4', '80mm_receipt')),
                is_default INTEGER DEFAULT 0,
                configuration TEXT,
                created_at_utc TEXT NOT NULL
            )
        """)
        
        # Products table (master data)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                code TEXT UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                unit TEXT DEFAULT 'KG',
                is_active INTEGER DEFAULT 1,
                created_at_utc TEXT NOT NULL
            )
        """)
        
        # Parties table (customers/suppliers)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS parties (
                id TEXT PRIMARY KEY,
                code TEXT UNIQUE,
                name TEXT NOT NULL,
                type TEXT CHECK (type IN ('Customer', 'Supplier', 'Both')),
                address TEXT,
                phone TEXT,
                email TEXT,
                is_active INTEGER DEFAULT 1,
                created_at_utc TEXT NOT NULL
            )
        """)
        
        # Transporters table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transporters (
                id TEXT PRIMARY KEY,
                code TEXT UNIQUE,
                name TEXT NOT NULL,
                license_no TEXT,
                phone TEXT,
                is_active INTEGER DEFAULT 1,
                created_at_utc TEXT NOT NULL
            )
        """)
        
        # Main transactions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                ticket_no INTEGER UNIQUE NOT NULL,
                vehicle_no TEXT NOT NULL,
                product_id TEXT,
                party_id TEXT,
                transporter_id TEXT,
                do_po_no TEXT,
                mode TEXT NOT NULL CHECK (mode IN ('two_pass', 'fixed_tare')),
                status TEXT NOT NULL CHECK (status IN ('pending', 'complete', 'void')),
                net_weight REAL,
                notes TEXT,
                operator_open_id TEXT NOT NULL,
                operator_close_id TEXT,
                opened_at_utc TEXT NOT NULL,
                closed_at_utc TEXT,
                voided_at_utc TEXT,
                void_reason TEXT,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (party_id) REFERENCES parties(id),
                FOREIGN KEY (transporter_id) REFERENCES transporters(id),
                FOREIGN KEY (operator_open_id) REFERENCES users(id),
                FOREIGN KEY (operator_close_id) REFERENCES users(id)
            )
        """)
        
        # Weigh events table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weigh_events (
                id TEXT PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                seq INTEGER NOT NULL CHECK (seq IN (1, 2)),
                gross_flag INTEGER NOT NULL CHECK (gross_flag IN (0, 1)),
                weight REAL NOT NULL,
                stable INTEGER NOT NULL CHECK (stable IN (0, 1)),
                captured_at_utc TEXT NOT NULL,
                raw_payload TEXT,
                photo_path TEXT,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id),
                UNIQUE(transaction_id, seq)
            )
        """)
        
        # Audit log table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                operator_id TEXT NOT NULL,
                action TEXT NOT NULL,
                entity TEXT NOT NULL,
                entity_id TEXT,
                reason TEXT,
                before_state TEXT,
                after_state TEXT,
                logged_at_utc TEXT NOT NULL,
                FOREIGN KEY (operator_id) REFERENCES users(id)
            )
        """)
    
    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """Create database indexes for performance"""
        
        # Transaction indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_vehicle_status ON transactions(vehicle_no, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_opened_at ON transactions(opened_at_utc)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_ticket_no ON transactions(ticket_no)")
        
        # Weigh events indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_weigh_events_transaction ON weigh_events(transaction_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_weigh_events_captured_at ON weigh_events(captured_at_utc)")
        
        # Audit log indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_operator ON audit_log(operator_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_logged_at ON audit_log(logged_at_utc)")
        
        # Partial unique index for pending transactions per vehicle
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_vehicle_pending ON transactions(vehicle_no) WHERE status = 'pending'")
    
    def _insert_default_data(self, conn: sqlite3.Connection) -> None:
        """Insert default data and settings"""
        
        current_time = datetime.utcnow().isoformat()
        
        # Create default admin user
        admin_id = str(uuid.uuid4())
        conn.execute("""
            INSERT OR IGNORE INTO users (id, username, pin_hash, role, created_at_utc)
            VALUES (?, 'admin', NULL, 'Admin', ?)
        """, (admin_id, current_time))
        
        # Default settings
        default_settings = [
            ('serial_port', 'COM1', 'string', 'Serial port for weight indicator'),
            ('serial_baud_rate', '9600', 'integer', 'Serial communication baud rate'),
            ('serial_data_bits', '8', 'integer', 'Serial data bits'),
            ('serial_parity', 'None', 'string', 'Serial parity setting'),
            ('serial_stop_bits', '1', 'integer', 'Serial stop bits'),
            ('weight_decimal_places', '2', 'integer', 'Decimal places for weight display'),
            ('weight_rounding_mode', 'round_half_up', 'string', 'Weight rounding mode'),
            ('stable_weight_threshold', '0.5', 'float', 'Threshold for stable weight detection'),
            ('stable_weight_duration', '3', 'integer', 'Duration in seconds for stable weight'),
            ('ticket_prefix', 'SC', 'string', 'Ticket number prefix'),
            ('ticket_sequence_reset', 'yearly', 'string', 'Ticket sequence reset frequency'),
            ('stale_pending_hours', '24', 'integer', 'Hours after which pending transactions are stale'),
            ('auto_backup_enabled', '1', 'boolean', 'Enable automatic database backups'),
            ('backup_retention_days', '30', 'integer', 'Number of days to retain backups'),
            ('application_mode', 'LIVE', 'string', 'Application mode (LIVE or TEST)'),
            ('locale', 'en_US', 'string', 'Application locale'),
            ('date_format', '%Y-%m-%d', 'string', 'Date display format'),
            ('time_format', '%H:%M:%S', 'string', 'Time display format')
        ]
        
        for key, value, data_type, description in default_settings:
            conn.execute("""
                INSERT OR IGNORE INTO settings (key, value, data_type, description, updated_at_utc, updated_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (key, value, data_type, description, current_time, admin_id))
        
        # Default printer
        printer_id = str(uuid.uuid4())
        conn.execute("""
            INSERT OR IGNORE INTO printers (id, name, type, is_default, created_at_utc)
            VALUES (?, 'Default Printer', 'A4', 1, ?)
        """, (printer_id, current_time))
    
    def schedule_vacuum(self, conn: sqlite3.Connection) -> None:
        """Schedule database vacuum operation"""
        # Check if vacuum is needed (when WAL file is > 1000 pages)
        result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if result and result[1] > 1000:  # wal_checkpoint returns (busy, log, checkpointed)
            conn.execute("VACUUM")
    
    def get_database_stats(self) -> dict:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Get table counts
            tables = ['transactions', 'weigh_events', 'vehicles', 'users', 'audit_log']
            for table in tables:
                result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                stats[f"{table}_count"] = result[0] if result else 0
            
            # Get database size
            stats['database_size_bytes'] = self.db_path.stat().st_size if self.db_path.exists() else 0
            
            # Get pending transactions
            result = conn.execute("SELECT COUNT(*) FROM transactions WHERE status = 'pending'").fetchone()
            stats['pending_transactions'] = result[0] if result else 0
            
            return stats


if __name__ == "__main__":
    # Test database creation
    schema = DatabaseSchema("../data/scale_system.db")
    schema.initialize_database()
    print("Database initialized successfully")
    print("Database stats:", schema.get_database_stats())
