#!/usr/bin/env python3
"""
SCALE System Hardware Configuration
Manages hardware profiles and diagnostic tools
"""

from typing import Dict, List, Any
from dataclasses import dataclass, asdict
import json
from pathlib import Path

@dataclass
class SerialProfile:
    """Serial communication profile with validation"""
    name: str
    port: str
    baud_rate: int = 9600
    data_bits: int = 8
    parity: str = 'N'  # N, E, O
    stop_bits: int = 1
    timeout: float = 1.0
    protocol: str = 'generic'
    message_format: str = 'csv'
    start_char: str = None
    end_char: str = '\r\n'
    stable_indicator: str = 'ST'
    weight_pattern: str = r'([+-]?\d+\.?\d*)'
    stable_threshold: float = 0.5
    stable_duration: int = 3
    
    def __post_init__(self):
        # Validate settings - Focus on RS232 standard baud rates
        # User specifically requested: 9600, 19200, 38400, 115200
        supported_baud_rates = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
        if self.baud_rate not in supported_baud_rates:
            raise ValueError(f"Invalid baud rate: {self.baud_rate}. Supported rates: {supported_baud_rates}")
        
        if self.data_bits not in [5, 6, 7, 8]:
            raise ValueError(f"Invalid data bits: {self.data_bits}")
        
        if self.parity not in ['N', 'E', 'O']:
            raise ValueError(f"Invalid parity: {self.parity}")
        
        if self.stop_bits not in [1, 1.5, 2]:
            raise ValueError(f"Invalid stop bits: {self.stop_bits}")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SerialProfile':
        """Create from dictionary"""
        return cls(**data)

class HardwareProfileManager:
    """Manages hardware profiles"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.profiles_file = self.config_dir / "hardware_profiles.json"
        
        # Load profiles
        self.profiles = self._load_profiles()
        
        # Ensure default profile exists
        if not self.profiles:
            self._create_default_profiles()
    
    def _load_profiles(self) -> Dict[str, SerialProfile]:
        """Load profiles from file"""
        
        if not self.profiles_file.exists():
            return {}
        
        try:
            with open(self.profiles_file, 'r') as f:
                data = json.load(f)
            
            profiles = {}
            for name, profile_data in data.items():
                profiles[name] = SerialProfile.from_dict(profile_data)
            
            return profiles
            
        except Exception as e:
            print(f"Error loading profiles: {e}")
            return {}
    
    def _save_profiles(self):
        """Save profiles to file"""
        
        try:
            data = {}
            for name, profile in self.profiles.items():
                data[name] = profile.to_dict()
            
            with open(self.profiles_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving profiles: {e}")
    
    def _create_default_profiles(self):
        """Create default hardware profiles"""
        
        # Generic profile
        self.profiles['Generic'] = SerialProfile(
            name='Generic',
            port='COM1',
            baud_rate=9600,
            protocol='generic',
            stable_indicator='ST',
            weight_pattern=r'([+-]?\d+\.?\d*)'
        )
        
        # RS232 Fast Profile (19200 baud)
        self.profiles['RS232_Fast'] = SerialProfile(
            name='RS232_Fast',
            port='COM1',
            baud_rate=19200,
            protocol='generic',
            stable_indicator='ST',
            weight_pattern=r'([+-]?\d+\.?\d*)',
            timeout=0.5  # Faster timeout for higher baud rate
        )
        
        # RS232 High Speed Profile (38400 baud)
        self.profiles['RS232_HighSpeed'] = SerialProfile(
            name='RS232_HighSpeed',
            port='COM1',
            baud_rate=38400,
            protocol='generic',
            stable_indicator='ST',
            weight_pattern=r'([+-]?\d+\.?\d*)',
            timeout=0.3
        )
        
        # RS232 Ultra Fast Profile (115200 baud)
        self.profiles['RS232_Ultra'] = SerialProfile(
            name='RS232_Ultra',
            port='COM1',
            baud_rate=115200,
            protocol='generic',
            stable_indicator='ST',
            weight_pattern=r'([+-]?\d+\.?\d*)',
            timeout=0.1
        )
        
        # Toledo profile
        self.profiles['Toledo'] = SerialProfile(
            name='Toledo',
            port='COM1',
            baud_rate=9600,
            protocol='toledo',
            stable_indicator='ST',
            weight_pattern=r'([+-]?\d+\.?\d*)\s*(kg|lb|g)',
            end_char='\r\n'
        )
        
        # Avery profile
        self.profiles['Avery'] = SerialProfile(
            name='Avery',
            port='COM1',
            baud_rate=9600,
            protocol='avery',
            stable_indicator='STABLE',
            weight_pattern=r'WEIGHT\s*([+-]?\d+\.?\d*)'
        )
        
        # Save default profiles
        self._save_profiles()
    
    def get_profile(self, name: str) -> SerialProfile:
        """Get profile by name"""
        
        if name not in self.profiles:
            raise ValueError(f"Profile '{name}' not found")
        
        return self.profiles[name]
    
    def get_all_profiles(self) -> Dict[str, SerialProfile]:
        """Get all profiles"""
        return self.profiles.copy()
    
    def create_profile(self, profile: SerialProfile) -> bool:
        """Create a new profile"""
        
        if profile.name in self.profiles:
            return False  # Profile already exists
        
        self.profiles[profile.name] = profile
        self._save_profiles()
        return True
    
    def update_profile(self, name: str, profile: SerialProfile) -> bool:
        """Update existing profile"""
        
        if name not in self.profiles:
            return False  # Profile doesn't exist
        
        # Update name if changed
        if name != profile.name:
            del self.profiles[name]
        
        self.profiles[profile.name] = profile
        self._save_profiles()
        return True
    
    def delete_profile(self, name: str) -> bool:
        """Delete profile"""
        
        if name not in self.profiles:
            return False
        
        if name == 'Generic':  # Don't allow deleting default profile
            return False
        
        del self.profiles[name]
        self._save_profiles()
        return True
    
    def get_available_ports(self) -> List[str]:
        """Get list of available serial ports"""
        
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            return [port.device for port in ports]
        except ImportError:
            # Return common port names if pyserial not available
            import platform
            system = platform.system()
            
            if system == 'Windows':
                return [f'COM{i}' for i in range(1, 21)]
            else:
                return ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyS0', '/dev/ttyS1']

class DiagnosticConsole:
    """Diagnostic console for monitoring serial communication"""
    
    def __init__(self, max_lines: int = 1000):
        self.max_lines = max_lines
        self.console_data = []
        self.filters = {
            'show_raw': True,
            'show_parsed': True,
            'show_errors': True,
            'show_status': True
        }
    
    def add_message(self, message_type: str, timestamp: str, data: Any):
        """Add message to console"""
        
        # Apply filters
        if message_type == 'raw_data' and not self.filters['show_raw']:
            return
        if message_type == 'weight_reading' and not self.filters['show_parsed']:
            return
        if message_type == 'error' and not self.filters['show_errors']:
            return
        if message_type == 'status' and not self.filters['show_status']:
            return
        
        # Format message
        formatted_message = self._format_message(message_type, timestamp, data)
        
        # Add to console
        self.console_data.append({
            'timestamp': timestamp,
            'type': message_type,
            'message': formatted_message,
            'data': data
        })
        
        # Trim if too many lines
        if len(self.console_data) > self.max_lines:
            self.console_data = self.console_data[-self.max_lines:]
    
    def _format_message(self, message_type: str, timestamp: str, data: Any) -> str:
        """Format message for display"""
        
        time_str = timestamp.split('T')[1][:8] if 'T' in timestamp else timestamp
        
        if message_type == 'raw_data':
            return f"[{time_str}] RAW: {data.get('data', '').strip()}"
        elif message_type == 'weight_reading':
            weight = data.get('weight', 0)
            stable = 'STABLE' if data.get('stable', False) else 'MOTION'
            unit = data.get('unit', 'KG')
            return f"[{time_str}] WEIGHT: {weight:.2f} {unit} ({stable})"
        elif message_type == 'error':
            return f"[{time_str}] ERROR: {data.get('message', 'Unknown error')}"
        elif message_type == 'status':
            status = data.get('status', 'unknown')
            port = data.get('port', 'unknown')
            return f"[{time_str}] STATUS: {status.upper()} on {port}"
        else:
            return f"[{time_str}] {message_type.upper()}: {str(data)}"
    
    def get_console_data(self, last_n: int = None) -> List[Dict]:
        """Get console data"""
        
        if last_n is None:
            return self.console_data.copy()
        else:
            return self.console_data[-last_n:]
    
    def clear_console(self):
        """Clear console data"""
        self.console_data.clear()
    
    def set_filter(self, filter_name: str, enabled: bool):
        """Set console filter"""
        if filter_name in self.filters:
            self.filters[filter_name] = enabled
    
    def get_filters(self) -> Dict[str, bool]:
        """Get current filters"""
        return self.filters.copy()
    
    def export_log(self, file_path: str, format_type: str = 'text') -> bool:
        """Export console log to file"""
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if format_type == 'json':
                    json.dump(self.console_data, f, indent=2)
                else:
                    for entry in self.console_data:
                        f.write(f"{entry['message']}\n")
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False

class PacketRecorder:
    """Records raw serial packets to file"""
    
    def __init__(self, log_file: str):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.file_handle = None
        self.is_recording = False
    
    def start_recording(self) -> bool:
        """Start packet recording"""
        
        try:
            self.file_handle = open(self.log_file, 'a', encoding='utf-8')
            self.is_recording = True
            
            # Write header
            from datetime import datetime
            self.file_handle.write(f"\n--- Recording started at {datetime.now().isoformat()} ---\n")
            self.file_handle.flush()
            
            return True
        except Exception as e:
            print(f"Failed to start recording: {e}")
            return False
    
    def stop_recording(self):
        """Stop packet recording"""
        
        if self.file_handle:
            from datetime import datetime
            self.file_handle.write(f"\n--- Recording stopped at {datetime.now().isoformat()} ---\n")
            self.file_handle.close()
            self.file_handle = None
        
        self.is_recording = False
    
    def record_packet(self, timestamp: str, raw_data: str):
        """Record a raw packet"""
        
        if self.is_recording and self.file_handle:
            try:
                self.file_handle.write(f"{timestamp}: {raw_data}")
                self.file_handle.flush()
            except Exception as e:
                print(f"Recording error: {e}")
    
    def get_log_size(self) -> int:
        """Get log file size in bytes"""
        
        if self.log_file.exists():
            return self.log_file.stat().st_size
        return 0
    
    def clear_log(self) -> bool:
        """Clear log file"""
        
        try:
            if self.is_recording:
                self.stop_recording()
            
            if self.log_file.exists():
                self.log_file.unlink()
            
            return True
        except Exception as e:
            print(f"Clear log error: {e}")
            return False


if __name__ == "__main__":
    # Test hardware configuration
    profile_manager = HardwareProfileManager()
    
    print("Available profiles:")
    for name in profile_manager.get_all_profiles():
        print(f"  - {name}")
    
    print("\nAvailable ports:")
    for port in profile_manager.get_available_ports():
        print(f"  - {port}")
    
    # Test diagnostic console
    console = DiagnosticConsole()
    console.add_message('status', '2024-01-01T10:00:00', {'status': 'connected', 'port': 'COM1'})
    console.add_message('weight_reading', '2024-01-01T10:00:01', {'weight': 1234.5, 'stable': True, 'unit': 'KG'})
    
    print("\nConsole messages:")
    for entry in console.get_console_data():
        print(f"  {entry['message']}")
