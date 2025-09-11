#!/usr/bin/env python3
"""
SCALE System RS232 Communication Manager
Specialized RS232 interface with enhanced diagnostics and configuration
"""

import serial
import serial.tools.list_ports
import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

class RS232Status(Enum):
    """RS232 connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    TESTING = "testing"

@dataclass
class RS232Config:
    """RS232 communication configuration"""
    port: str
    baud_rate: int = 9600  # 9600, 19200, 38400, 115200
    data_bits: int = 8
    parity: str = 'N'  # N=None, E=Even, O=Odd
    stop_bits: int = 1
    flow_control: str = 'none'  # none, xon_xoff, rts_cts, dsr_dtr
    timeout: float = 1.0
    write_timeout: float = 1.0
    
    # RS232 specific settings
    dtr: bool = True  # Data Terminal Ready
    rts: bool = True  # Request To Send
    
    def __post_init__(self):
        # Validate RS232 settings
        valid_baud_rates = [300, 600, 1200, 2400, 4800, 9600, 19200, 38400, 115200]
        if self.baud_rate not in valid_baud_rates:
            raise ValueError(f"Invalid baud rate: {self.baud_rate}. Must be one of {valid_baud_rates}")
        
        if self.data_bits not in [7, 8]:
            raise ValueError(f"Invalid data bits: {self.data_bits}. Must be 7 or 8")
        
        if self.parity not in ['N', 'E', 'O']:
            raise ValueError(f"Invalid parity: {self.parity}. Must be N, E, or O")
        
        if self.stop_bits not in [1, 2]:
            raise ValueError(f"Invalid stop bits: {self.stop_bits}. Must be 1 or 2")

@dataclass
class RS232TestResult:
    """RS232 connection test result"""
    success: bool
    port: str
    baud_rate: int
    response_time: float
    bytes_sent: int
    bytes_received: int
    error_message: Optional[str] = None
    raw_response: Optional[str] = None

class RS232Manager:
    """Enhanced RS232 communication manager"""
    
    def __init__(self):
        self.connection: Optional[serial.Serial] = None
        self.config: Optional[RS232Config] = None
        self.status = RS232Status.DISCONNECTED
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.stats = {
            'connection_attempts': 0,
            'successful_connections': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'last_connection_time': None,
            'total_uptime': 0,
            'error_count': 0
        }
        
        # Event callbacks
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None
        self.on_data_received: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
    
    def get_available_ports(self) -> List[Dict[str, str]]:
        """Get list of available RS232/serial ports with details"""
        
        ports = []
        try:
            for port_info in serial.tools.list_ports.comports():
                ports.append({
                    'device': port_info.device,
                    'name': port_info.name or 'Unknown',
                    'description': port_info.description or 'No description',
                    'manufacturer': port_info.manufacturer or 'Unknown',
                    'serial_number': port_info.serial_number or 'Unknown',
                    'vid': hex(port_info.vid) if port_info.vid else 'Unknown',
                    'pid': hex(port_info.pid) if port_info.pid else 'Unknown'
                })
        except Exception as e:
            self.logger.error(f"Error listing ports: {e}")
        
        return ports
    
    def test_connection(self, config: RS232Config, test_message: str = "TEST\r\n") -> RS232TestResult:
        """Test RS232 connection with specified configuration"""
        
        start_time = time.time()
        test_result = RS232TestResult(
            success=False,
            port=config.port,
            baud_rate=config.baud_rate,
            response_time=0,
            bytes_sent=0,
            bytes_received=0
        )
        
        temp_connection = None
        try:
            # Create test connection (will auto-open)
            temp_connection = self._create_serial_connection(config)
            
            # Verify it's open
            if not temp_connection.is_open:
                raise Exception("Failed to open serial port")
            
            # Clear buffers
            temp_connection.reset_input_buffer()
            temp_connection.reset_output_buffer()
            
            # Send test message
            test_bytes = test_message.encode('ascii')
            temp_connection.write(test_bytes)
            test_result.bytes_sent = len(test_bytes)
            
            # Wait for response (with timeout)
            time.sleep(0.1)  # Give device time to respond
            
            if temp_connection.in_waiting > 0:
                response = temp_connection.read(temp_connection.in_waiting)
                test_result.bytes_received = len(response)
                test_result.raw_response = response.decode('ascii', errors='ignore')
            
            test_result.success = True
            test_result.response_time = time.time() - start_time
            
        except Exception as e:
            test_result.error_message = str(e)
            test_result.response_time = time.time() - start_time
            
        finally:
            if temp_connection and temp_connection.is_open:
                temp_connection.close()
        
        return test_result
    
    def connect(self, config: RS232Config) -> bool:
        """Connect to RS232 port"""
        
        if self.is_connected():
            self.disconnect()
        
        self.status = RS232Status.CONNECTING
        self.stats['connection_attempts'] += 1
        
        try:
            self.connection = self._create_serial_connection(config)
            
            # Connection is automatically opened by pyserial
            if self.connection.is_open:
                self.config = config
                self.status = RS232Status.CONNECTED
                self.stats['successful_connections'] += 1
                self.stats['last_connection_time'] = datetime.now().isoformat()
                
                # Configure RS232 control lines
                self.connection.dtr = config.dtr
                self.connection.rts = config.rts
                
                # Clear buffers
                self.connection.reset_input_buffer()
                self.connection.reset_output_buffer()
                
                self.logger.info(f"Connected to {config.port} at {config.baud_rate} baud")
                
                if self.on_connect:
                    self.on_connect(config)
                
                return True
            
        except Exception as e:
            self.status = RS232Status.ERROR
            self.stats['error_count'] += 1
            error_msg = f"Connection failed: {e}"
            self.logger.error(error_msg)
            
            if self.on_error:
                self.on_error(error_msg)
        
        return False
    
    def disconnect(self):
        """Disconnect from RS232 port"""
        
        if self.connection and self.connection.is_open:
            try:
                self.connection.close()
                self.logger.info(f"Disconnected from {self.config.port if self.config else 'unknown port'}")
                
                if self.on_disconnect:
                    self.on_disconnect()
                    
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")
        
        self.connection = None
        self.config = None
        self.status = RS232Status.DISCONNECTED
    
    def is_connected(self) -> bool:
        """Check if RS232 connection is active"""
        return (self.connection is not None and 
                self.connection.is_open and 
                self.status == RS232Status.CONNECTED)
    
    def send_data(self, data: str) -> bool:
        """Send data over RS232"""
        
        if not self.is_connected():
            return False
        
        try:
            data_bytes = data.encode('ascii')
            bytes_written = self.connection.write(data_bytes)
            self.stats['bytes_sent'] += bytes_written
            
            self.logger.debug(f"Sent {bytes_written} bytes: {repr(data)}")
            return bytes_written == len(data_bytes)
            
        except Exception as e:
            self.logger.error(f"Send error: {e}")
            self.stats['error_count'] += 1
            
            if self.on_error:
                self.on_error(f"Send error: {e}")
            
            return False
    
    def read_data(self, timeout: Optional[float] = None) -> Optional[str]:
        """Read data from RS232"""
        
        if not self.is_connected():
            return None
        
        try:
            # Set timeout if provided
            original_timeout = self.connection.timeout
            if timeout is not None:
                self.connection.timeout = timeout
            
            # Check for available data
            if self.connection.in_waiting > 0:
                data = self.connection.read(self.connection.in_waiting)
                self.stats['bytes_received'] += len(data)
                
                decoded_data = data.decode('ascii', errors='ignore')
                self.logger.debug(f"Received {len(data)} bytes: {repr(decoded_data)}")
                
                if self.on_data_received:
                    self.on_data_received(decoded_data)
                
                return decoded_data
            
            # Restore original timeout
            if timeout is not None:
                self.connection.timeout = original_timeout
            
        except Exception as e:
            self.logger.error(f"Read error: {e}")
            self.stats['error_count'] += 1
            
            if self.on_error:
                self.on_error(f"Read error: {e}")
        
        return None
    
    def flush_buffers(self):
        """Flush input and output buffers"""
        
        if self.is_connected():
            try:
                self.connection.reset_input_buffer()
                self.connection.reset_output_buffer()
                self.logger.debug("Buffers flushed")
            except Exception as e:
                self.logger.error(f"Flush error: {e}")
    
    def get_port_status(self) -> Dict:
        """Get detailed port status information"""
        
        status_info = {
            'connected': self.is_connected(),
            'status': self.status.value,
            'port': self.config.port if self.config else None,
            'baud_rate': self.config.baud_rate if self.config else None,
            'statistics': self.stats.copy()
        }
        
        if self.is_connected():
            try:
                status_info.update({
                    'dsr': self.connection.dsr,  # Data Set Ready
                    'cts': self.connection.cts,  # Clear To Send
                    'ri': self.connection.ri,    # Ring Indicator
                    'cd': self.connection.cd,    # Carrier Detect
                    'dtr': self.connection.dtr,  # Data Terminal Ready
                    'rts': self.connection.rts,  # Request To Send
                    'in_waiting': self.connection.in_waiting,
                    'out_waiting': self.connection.out_waiting
                })
            except Exception as e:
                status_info['status_error'] = str(e)
        
        return status_info
    
    def _create_serial_connection(self, config: RS232Config) -> serial.Serial:
        """Create serial connection with RS232 configuration"""
        
        # Map parity settings
        parity_map = {
            'N': serial.PARITY_NONE,
            'E': serial.PARITY_EVEN,
            'O': serial.PARITY_ODD
        }
        
        # Map flow control
        xonxoff = config.flow_control == 'xon_xoff'
        rtscts = config.flow_control == 'rts_cts'
        dsrdtr = config.flow_control == 'dsr_dtr'
        
        return serial.Serial(
            port=config.port,
            baudrate=config.baud_rate,
            bytesize=config.data_bits,
            parity=parity_map[config.parity],
            stopbits=config.stop_bits,
            timeout=config.timeout,
            write_timeout=config.write_timeout,
            xonxoff=xonxoff,
            rtscts=rtscts,
            dsrdtr=dsrdtr
            # Removed do_not_open parameter for better compatibility
        )
    
    def auto_detect_baud_rate(self, port: str, test_message: str = "TEST\r\n") -> Optional[int]:
        """Auto-detect baud rate by testing common rates"""
        
        test_rates = [300, 600, 1200, 2400, 4800, 9600, 19200, 38400, 115200]  # User requested rates
        
        for baud_rate in test_rates:
            self.logger.info(f"Testing baud rate {baud_rate}...")
            
            config = RS232Config(
                port=port,
                baud_rate=baud_rate
            )
            
            result = self.test_connection(config, test_message)
            
            if result.success and result.bytes_received > 0:
                self.logger.info(f"Auto-detected baud rate: {baud_rate}")
                return baud_rate
        
        self.logger.warning("Could not auto-detect baud rate")
        return None
