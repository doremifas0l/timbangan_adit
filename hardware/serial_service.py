#!/usr/bin/env python3
"""
SCALE System Hardware Abstraction Layer - Serial Communication Service
Handles all serial communication with weight indicators in a dedicated background thread
"""

import time
import queue
import serial
import threading
import os
from datetime import datetime
from typing import Dict, Optional, Callable, Any
import json
import re
from dataclasses import dataclass
from enum import Enum

class SerialStatus(Enum):
    """Serial connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

@dataclass
class WeightReading:
    """Weight reading data structure"""
    weight: float
    stable: bool
    unit: str = "KG"
    timestamp: str = None
    raw_data: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

@dataclass
class SerialProfile:
    """Serial communication profile"""
    port: str
    baud_rate: int = 9600
    data_bits: int = 8
    parity: str = 'N'  # N, E, O
    stop_bits: int = 1
    timeout: float = 1.0
    protocol: str = 'generic'  # generic, toledo, avery, etc.
    message_format: str = 'csv'  # csv, fixed, custom
    start_char: str = None
    end_char: str = '\r\n'
    stable_indicator: str = 'ST'  # What indicates stable weight
    weight_pattern: str = r'([+-]?\d+\.?\d*)'
    
class SerialProtocolParser:
    """Parses different weight indicator protocols"""
    
    def __init__(self, profile: SerialProfile):
        self.profile = profile
        self.weight_pattern = re.compile(profile.weight_pattern)
    
    def parse_message(self, raw_data: str) -> Optional[WeightReading]:
        """Parse raw serial message into weight reading"""
        
        try:
            if self.profile.protocol == 'generic':
                return self._parse_generic(raw_data)
            elif self.profile.protocol == 'toledo':
                return self._parse_toledo(raw_data)
            elif self.profile.protocol == 'avery':
                return self._parse_avery(raw_data)
            else:
                return self._parse_custom(raw_data)
                
        except Exception as e:
            print(f"Parse error: {e}")
            return None
    
    def _parse_generic(self, data: str) -> Optional[WeightReading]:
        """Parse generic CSV format: weight,stable,unit"""
        
        # Clean the data
        data = data.strip()
        
        # Extract weight using regex
        weight_match = self.weight_pattern.search(data)
        if not weight_match:
            return None
        
        weight = float(weight_match.group(1))
        
        # Check for stable indicator
        stable = self.profile.stable_indicator in data
        
        # Extract unit (default to KG)
        unit = 'KG'
        if 'LB' in data.upper():
            unit = 'LB'
        elif 'G' in data.upper():
            unit = 'G'
        
        return WeightReading(
            weight=weight,
            stable=stable,
            unit=unit,
            raw_data=data
        )
    
    def _parse_toledo(self, data: str) -> Optional[WeightReading]:
        """Parse Toledo protocol format"""
        
        # Toledo format: +001234.5 kg ST
        data = data.strip()
        
        # Extract weight
        weight_match = re.search(r'([+-]?\d+\.?\d*)', data)
        if not weight_match:
            return None
        
        weight = float(weight_match.group(1))
        
        # Check stability
        stable = 'ST' in data.upper()
        
        # Extract unit
        unit = 'KG'
        if 'LB' in data.upper():
            unit = 'LB'
        
        return WeightReading(
            weight=weight,
            stable=stable,
            unit=unit,
            raw_data=data
        )
    
    def _parse_avery(self, data: str) -> Optional[WeightReading]:
        """Parse Avery protocol format"""
        
        # Avery format varies, implement based on specific model
        return self._parse_generic(data)
    
    def _parse_custom(self, data: str) -> Optional[WeightReading]:
        """Parse custom format based on profile settings"""
        
        return self._parse_generic(data)

class StableWeightDetector:
    """Detects stable weight readings"""
    
    def __init__(self, threshold: float = 0.5, duration: int = 3):
        self.threshold = threshold  # Weight difference threshold
        self.duration = duration    # Duration in seconds
        self.readings = []
        self.last_stable = None
    
    def add_reading(self, weight: float) -> bool:
        """Add weight reading and check if stable"""
        
        current_time = time.time()
        
        # Add reading with timestamp
        self.readings.append((weight, current_time))
        
        # Remove old readings
        cutoff_time = current_time - self.duration
        self.readings = [(w, t) for w, t in self.readings if t > cutoff_time]
        
        # Check if we have enough readings
        if len(self.readings) < 2:
            return False
        
        # Check if all recent readings are within threshold
        weights = [w for w, t in self.readings]
        min_weight = min(weights)
        max_weight = max(weights)
        
        is_stable = (max_weight - min_weight) <= self.threshold
        
        if is_stable:
            self.last_stable = weight
        
        return is_stable
    
    def get_stable_weight(self) -> Optional[float]:
        """Get the last stable weight"""
        return self.last_stable

def get_serial_service(profile: SerialProfile, message_queue: queue.Queue):
    """Factory function to get appropriate serial service (real or mock)"""
    
    # Check if we're in test mode
    if os.getenv('SCALE_TEST_MODE') == '1':
        print("[TEST] TEST MODE: Using mock serial service")
        try:
            from ..testing.mock_serial_service import MockSerialService
            return MockSerialService(profile)
        except ImportError:
            print("[WARNING] Mock serial service not available, using real service")
            pass
    
    # Return real serial service
    return SerialService(profile, message_queue)

class SerialService(threading.Thread):
    """Background serial communication service"""
    
    def __init__(self, profile: SerialProfile, message_queue: queue.Queue):
        super().__init__(daemon=True)
        self.profile = profile
        self.message_queue = message_queue
        self.serial_connection = None
        self.status = SerialStatus.DISCONNECTED
        self.running = False
        self.reconnect_interval = 5  # seconds
        
        # Components
        self.parser = SerialProtocolParser(profile)
        self.stable_detector = StableWeightDetector()
        
        # Diagnostics
        self.raw_data_logger = None
        self.packet_recorder_enabled = False
        self.stats = {
            'messages_received': 0,
            'messages_parsed': 0,
            'parse_errors': 0,
            'connection_attempts': 0,
            'last_connection_attempt': None,
            'last_successful_read': None
        }
    
    def start_service(self):
        """Start the serial service"""
        self.running = True
        self.start()
        
        # Send initial status
        self._send_status_message()
    
    def stop_service(self):
        """Stop the serial service"""
        self.running = False
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.join(timeout=2.0)
    
    def update_profile(self, new_profile: SerialProfile):
        """Update serial profile (requires restart)"""
        self.profile = new_profile
        self.parser = SerialProtocolParser(new_profile)
        
        # Reconnect with new settings
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        
        self._send_message('profile_updated', {'profile': new_profile.__dict__})
    
    def enable_packet_recorder(self, log_file: str):
        """Enable packet recording to file"""
        try:
            self.raw_data_logger = open(log_file, 'a', encoding='utf-8')
            self.packet_recorder_enabled = True
            self._send_message('packet_recorder', {'enabled': True, 'file': log_file})
        except Exception as e:
            self._send_message('error', {'message': f'Failed to enable packet recorder: {e}'})
    
    def disable_packet_recorder(self):
        """Disable packet recording"""
        if self.raw_data_logger:
            self.raw_data_logger.close()
            self.raw_data_logger = None
        self.packet_recorder_enabled = False
        self._send_message('packet_recorder', {'enabled': False})
    
    def get_statistics(self) -> Dict:
        """Get service statistics"""
        return {
            **self.stats,
            'status': self.status.value,
            'profile': self.profile.__dict__,
            'running': self.running
        }
    
    def run(self):
        """Main service thread loop"""
        
        while self.running:
            try:
                if self.status != SerialStatus.CONNECTED:
                    self._attempt_connection()
                
                if self.status == SerialStatus.CONNECTED:
                    self._read_data()
                else:
                    time.sleep(self.reconnect_interval)
                    
            except Exception as e:
                self._handle_error(f"Service error: {e}")
                time.sleep(self.reconnect_interval)
    
    def _attempt_connection(self):
        """Attempt to connect to serial port"""
        
        try:
            self.status = SerialStatus.CONNECTING
            self.stats['connection_attempts'] += 1
            self.stats['last_connection_attempt'] = datetime.utcnow().isoformat()
            
            self._send_status_message()
            
            # Configure serial connection
            parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
            
            self.serial_connection = serial.Serial(
                port=self.profile.port,
                baudrate=self.profile.baud_rate,
                bytesize=self.profile.data_bits,
                parity=parity_map.get(self.profile.parity, serial.PARITY_NONE),
                stopbits=self.profile.stop_bits,
                timeout=self.profile.timeout
            )
            
            if self.serial_connection.is_open:
                self.status = SerialStatus.CONNECTED
                self._send_message('connected', {'port': self.profile.port})
                self._send_status_message()
            
        except Exception as e:
            self._handle_error(f"Connection failed: {e}")
    
    def _read_data(self):
        """Read data from serial port"""
        
        try:
            if self.serial_connection and self.serial_connection.in_waiting > 0:
                # Read line
                raw_data = self.serial_connection.readline().decode('utf-8', errors='ignore')
                
                if raw_data:
                    self.stats['messages_received'] += 1
                    self.stats['last_successful_read'] = datetime.utcnow().isoformat()
                    
                    # Log raw data if recorder enabled
                    if self.packet_recorder_enabled and self.raw_data_logger:
                        timestamp = datetime.utcnow().isoformat()
                        self.raw_data_logger.write(f"{timestamp}: {raw_data}")
                        self.raw_data_logger.flush()
                    
                    # Send raw data for console
                    self._send_message('raw_data', {'data': raw_data})
                    
                    # Parse the message
                    reading = self.parser.parse_message(raw_data)
                    
                    if reading:
                        self.stats['messages_parsed'] += 1
                        
                        # Check stability using our detector
                        is_stable = self.stable_detector.add_reading(reading.weight)
                        
                        # Override stability if parser detected it
                        if reading.stable:
                            is_stable = True
                            self.stable_detector.last_stable = reading.weight
                        
                        # Send weight reading
                        self._send_message('weight_reading', {
                            'weight': reading.weight,
                            'stable': is_stable,
                            'unit': reading.unit,
                            'timestamp': reading.timestamp,
                            'raw_data': reading.raw_data
                        })
                    else:
                        self.stats['parse_errors'] += 1
            else:
                # Small delay to prevent busy waiting
                time.sleep(0.1)
                
        except Exception as e:
            self._handle_error(f"Read error: {e}")
    
    def _handle_error(self, error_message: str):
        """Handle errors and update status"""
        
        self.status = SerialStatus.ERROR
        
        # Close connection if open
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.close()
            except:
                pass
        
        self.serial_connection = None
        
        # Send error message
        self._send_message('error', {'message': error_message})
        self._send_status_message()
        
        # Reset to disconnected after a delay
        time.sleep(1.0)
        self.status = SerialStatus.DISCONNECTED
    
    def _send_message(self, message_type: str, data: Dict):
        """Send message to the message queue"""
        
        message = {
            'type': message_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        try:
            self.message_queue.put_nowait(message)
        except queue.Full:
            # Remove oldest message and add new one
            try:
                self.message_queue.get_nowait()
                self.message_queue.put_nowait(message)
            except queue.Empty:
                pass
    
    def _send_status_message(self):
        """Send current status"""
        self._send_message('status', {
            'status': self.status.value,
            'port': self.profile.port,
            'connected': self.status == SerialStatus.CONNECTED
        })

class HardwareManager:
    """Main hardware manager class"""
    
    def __init__(self, profile: SerialProfile):
        self.profile = profile
        self.message_queue = queue.Queue(maxsize=1000)
        self.serial_service = None
        self.message_handlers = {}
        
        # Start serial service
        self.start_serial_service()
    
    def start_serial_service(self):
        """Start the serial communication service"""
        
        if self.serial_service:
            self.serial_service.stop_service()
        
        self.serial_service = SerialService(self.profile, self.message_queue)
        self.serial_service.start_service()
    
    def stop_serial_service(self):
        """Stop the serial communication service"""
        
        if self.serial_service:
            self.serial_service.stop_service()
            self.serial_service = None
    
    def update_profile(self, new_profile: SerialProfile):
        """Update serial profile"""
        
        self.profile = new_profile
        if self.serial_service:
            self.serial_service.update_profile(new_profile)
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler"""
        self.message_handlers[message_type] = handler
    
    def process_messages(self) -> int:
        """Process pending messages and return count processed"""
        
        processed = 0
        
        while True:
            try:
                message = self.message_queue.get_nowait()
                message_type = message.get('type')
                
                # Call registered handler if exists
                if message_type in self.message_handlers:
                    try:
                        self.message_handlers[message_type](message)
                    except Exception as e:
                        print(f"Handler error for {message_type}: {e}")
                
                processed += 1
                
            except queue.Empty:
                break
        
        return processed
    
    def get_statistics(self) -> Dict:
        """Get hardware statistics"""
        
        stats = {
            'queue_size': self.message_queue.qsize(),
            'queue_maxsize': self.message_queue.maxsize
        }
        
        if self.serial_service:
            stats.update(self.serial_service.get_statistics())
        
        return stats
    
    def enable_diagnostics(self, log_file: Optional[str] = None):
        """Enable diagnostic features"""
        
        if self.serial_service and log_file:
            self.serial_service.enable_packet_recorder(log_file)
    
    def disable_diagnostics(self):
        """Disable diagnostic features"""
        
        if self.serial_service:
            self.serial_service.disable_packet_recorder()


if __name__ == "__main__":
    # Test hardware manager
    profile = SerialProfile(
        port='COM1',
        baud_rate=9600,
        protocol='generic'
    )
    
    manager = HardwareManager(profile)
    
    # Register handlers
    def on_weight_reading(message):
        data = message['data']
        print(f"Weight: {data['weight']} {data['unit']} (Stable: {data['stable']})")
    
    def on_status(message):
        data = message['data']
        print(f"Status: {data['status']} on {data['port']}")
    
    manager.register_handler('weight_reading', on_weight_reading)
    manager.register_handler('status', on_status)
    
    try:
        while True:
            count = manager.process_messages()
            if count > 0:
                print(f"Processed {count} messages")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping service...")
        manager.stop_serial_service()
