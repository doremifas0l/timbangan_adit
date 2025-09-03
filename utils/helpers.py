#!/usr/bin/env python3
"""
SCALE System Utilities
Common utility functions and helpers
"""

import hashlib
import uuid
import re
import json
import csv
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, ROUND_HALF_UP
import qrcode
from io import BytesIO
import base64
from pathlib import Path

def generate_uuid() -> str:
    """Generate a UUID string"""
    return str(uuid.uuid4())

def create_directory(directory_path: str) -> bool:
    """Create directory if it doesn't exist"""
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {directory_path}: {e}")
        return False

def format_timestamp(dt: datetime) -> str:
    """Format timestamp for display"""
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def hash_pin(pin: str) -> str:
    """Hash a PIN using SHA-256"""
    return hashlib.sha256(pin.encode()).hexdigest()

def verify_pin(pin: str, pin_hash: str) -> bool:
    """Verify PIN against hash"""
    return hash_pin(pin) == pin_hash

def format_weight(weight: float, decimal_places: int = 2, unit: str = 'KG') -> str:
    """Format weight for display"""
    if weight is None:
        return 'N/A'
    
    formatted = f"{weight:.{decimal_places}f}"
    return f"{formatted} {unit}"

def round_weight(weight: float, decimal_places: int = 2, rounding_mode: str = 'round_half_up') -> float:
    """Round weight using specified rounding mode"""
    if weight is None:
        return None
    
    decimal_weight = Decimal(str(weight))
    
    if rounding_mode == 'round_half_up':
        rounded = decimal_weight.quantize(
            Decimal('0.' + '0' * decimal_places),
            rounding=ROUND_HALF_UP
        )
    else:
        # Default Python rounding
        rounded = round(decimal_weight, decimal_places)
    
    return float(rounded)

def format_datetime(dt: Union[str, datetime], format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Format datetime for display"""
    if isinstance(dt, str):
        try:
            # Parse ISO format
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return dt  # Return as-is if can't parse
    
    if isinstance(dt, datetime):
        return dt.strftime(format_str)
    
    return str(dt)

def parse_datetime(dt_str: str) -> Optional[datetime]:
    """Parse datetime string"""
    if not dt_str:
        return None
    
    # Common formats to try
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%d'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    
    # Try ISO format parsing
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        return None

def validate_vehicle_number(vehicle_no: str) -> bool:
    """Validate vehicle number format"""
    if not vehicle_no:
        return False
    
    # Basic validation: alphanumeric and hyphens, max 20 chars
    pattern = r'^[A-Z0-9-]{1,20}$'
    return bool(re.match(pattern, vehicle_no.upper()))

def validate_pin(pin: str) -> bool:
    """Validate PIN format"""
    if not pin:
        return True  # PIN is optional
    
    # 4-6 digits
    pattern = r'^\d{4,6}$'
    return bool(re.match(pattern, pin))

def validate_username(username: str) -> bool:
    """Validate username format"""
    if not username:
        return False
    
    # 3-20 characters, alphanumeric and underscore
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return bool(re.match(pattern, username))

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove multiple underscores
    sanitized = re.sub(r'_{2,}', '_', sanitized)
    
    # Trim and limit length
    sanitized = sanitized.strip('_')[:100]
    
    return sanitized

def generate_ticket_hash(ticket_data: Dict) -> str:
    """Generate SHA-256 hash for ticket verification"""
    # Create string from key ticket data
    hash_string = f"{ticket_data.get('ticket_no', '')}"
    hash_string += f"{ticket_data.get('vehicle_no', '')}"
    hash_string += f"{ticket_data.get('net_weight', '')}"
    hash_string += f"{ticket_data.get('closed_at_utc', '')}"
    
    return hashlib.sha256(hash_string.encode()).hexdigest()[:16]  # First 16 chars

def generate_qr_code(data: str, size: int = 10) -> str:
    """Generate QR code as base64 encoded image"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"QR code generation error: {e}")
        return ""

def export_to_csv(data: List[Dict], filename: str, columns: Optional[List[str]] = None) -> bool:
    """Export data to CSV file"""
    try:
        if not data:
            return False
        
        if columns is None:
            columns = list(data[0].keys())
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            
            for row in data:
                # Filter row to include only specified columns
                filtered_row = {col: row.get(col, '') for col in columns}
                writer.writerow(filtered_row)
        
        return True
    except Exception as e:
        print(f"CSV export error: {e}")
        return False

def export_to_json(data: Any, filename: str) -> bool:
    """Export data to JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, default=str)
        return True
    except Exception as e:
        print(f"JSON export error: {e}")
        return False

def calculate_age_hours(timestamp_str: str) -> float:
    """Calculate age in hours from timestamp"""
    try:
        timestamp = parse_datetime(timestamp_str)
        if timestamp:
            now = datetime.utcnow()
            delta = now - timestamp
            return delta.total_seconds() / 3600
    except Exception:
        pass
    return 0.0

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"

def get_next_ticket_number(current_max: int, prefix: str = '', reset_mode: str = 'yearly') -> int:
    """Get next ticket number based on reset mode"""
    # For now, just increment. Future versions can implement date-based resets
    return (current_max or 0) + 1

def format_ticket_number(ticket_no: int, prefix: str = 'SC', padding: int = 6) -> str:
    """Format ticket number with prefix and padding"""
    padded_number = str(ticket_no).zfill(padding)
    return f"{prefix}{padded_number}"

def parse_ticket_number(formatted_ticket: str, prefix: str = 'SC') -> Optional[int]:
    """Parse ticket number from formatted string"""
    if not formatted_ticket.startswith(prefix):
        return None
    
    try:
        number_str = formatted_ticket[len(prefix):]
        return int(number_str)
    except ValueError:
        return None

def calculate_net_weight(gross: float, tare: float, decimal_places: int = 2) -> float:
    """Calculate net weight with proper rounding"""
    if gross is None or tare is None:
        return None
    
    net = gross - tare
    return round_weight(net, decimal_places)

def validate_weight_range(weight: float, min_weight: float = 0.0, max_weight: float = 999999.99) -> bool:
    """Validate weight is within acceptable range"""
    if weight is None:
        return False
    
    return min_weight <= weight <= max_weight

def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human readable string"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def clean_string(text: str, max_length: int = None) -> str:
    """Clean and validate string input"""
    if not text:
        return ""
    
    # Remove extra whitespace
    cleaned = ' '.join(text.split())
    
    # Truncate if needed
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip()
    
    return cleaned

def safe_float_convert(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float"""
    if value is None:
        return default
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int_convert(value: Any, default: int = 0) -> int:
    """Safely convert value to int"""
    if value is None:
        return default
    
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


if __name__ == "__main__":
    # Test utilities
    print("Testing SCALE System utilities...")
    
    # Test weight formatting
    print(f"Weight: {format_weight(1234.567, 2, 'KG')}")
    
    # Test weight rounding
    print(f"Rounded: {round_weight(1234.567, 2)}")
    
    # Test validation
    print(f"Valid vehicle: {validate_vehicle_number('ABC-123')}")
    print(f"Valid PIN: {validate_pin('1234')}")
    
    # Test QR code generation
    qr_data = generate_qr_code('SCALE-001234')
    print(f"QR generated: {len(qr_data) > 0}")
    
    # Test ticket hash
    ticket_data = {
        'ticket_no': 1234,
        'vehicle_no': 'ABC-123',
        'net_weight': 5000.50,
        'closed_at_utc': '2024-01-01T10:00:00'
    }
    ticket_hash = generate_ticket_hash(ticket_data)
    print(f"Ticket hash: {ticket_hash}")
    
    print("Utilities test completed.")
