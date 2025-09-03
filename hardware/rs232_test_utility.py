#!/usr/bin/env python3
"""
RS232 Test Utility for SCALE System
Comprehensive testing tool for RS232 communication
"""

import time
import sys
from typing import Dict, List
from datetime import datetime
import argparse
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from hardware.rs232_manager import RS232Manager, RS232Config, RS232Status
from hardware.serial_service import SerialProfile, HardwareProfileManager

class RS232TestUtility:
    """Comprehensive RS232 testing utility"""
    
    def __init__(self):
        self.rs232_manager = RS232Manager()
        self.profile_manager = HardwareProfileManager()
        self.test_results = []
    
    def scan_ports(self) -> Dict:
        """Scan for available RS232 ports"""
        
        print("\n=== RS232 Port Scanner ===")
        print(f"Scan time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)
        
        ports = self.rs232_manager.get_available_ports()
        
        if not ports:
            print("No serial ports detected.")
            return {'ports': [], 'count': 0}
        
        print(f"Found {len(ports)} serial port(s):")
        print()
        
        for i, port in enumerate(ports, 1):
            print(f"{i}. {port['device']}")
            print(f"   Name: {port['name']}")
            print(f"   Description: {port['description']}")
            print(f"   Manufacturer: {port['manufacturer']}")
            if port['serial_number'] != 'Unknown':
                print(f"   Serial Number: {port['serial_number']}")
            print(f"   VID:PID: {port['vid']}:{port['pid']}")
            print()
        
        return {'ports': ports, 'count': len(ports)}
    
    def test_baud_rates(self, port: str, test_message: str = "SCALE_TEST\r\n") -> Dict:
        """Test all supported baud rates on a port"""
        
        print(f"\n=== Baud Rate Testing on {port} ===")
        print(f"Test message: {repr(test_message)}")
        print("-" * 50)
        
        baud_rates = [9600, 19200, 38400, 115200]
        results = []
        
        for baud_rate in baud_rates:
            print(f"Testing {baud_rate} baud...", end=" ")
            
            config = RS232Config(
                port=port,
                baud_rate=baud_rate,
                timeout=2.0
            )
            
            result = self.rs232_manager.test_connection(config, test_message)
            results.append({
                'baud_rate': baud_rate,
                'success': result.success,
                'response_time': result.response_time,
                'bytes_sent': result.bytes_sent,
                'bytes_received': result.bytes_received,
                'error': result.error_message,
                'response': result.raw_response
            })
            
            if result.success:
                status = f"OK ({result.response_time:.3f}s)"
                if result.bytes_received > 0:
                    status += f" - Got {result.bytes_received} bytes"
            else:
                status = f"FAILED - {result.error_message}"
            
            print(status)
        
        successful_rates = [r['baud_rate'] for r in results if r['success']]
        if successful_rates:
            print(f"\n✓ Working baud rates: {successful_rates}")
        else:
            print("\n✗ No baud rates responded successfully")
        
        return {
            'port': port,
            'test_message': test_message,
            'results': results,
            'successful_rates': successful_rates
        }
    
    def interactive_test(self, port: str, baud_rate: int = 9600):
        """Interactive RS232 communication test"""
        
        print(f"\n=== Interactive RS232 Test ===")
        print(f"Port: {port}")
        print(f"Baud Rate: {baud_rate}")
        print(f"Commands: 'quit' to exit, 'status' for port status, 'flush' to clear buffers")
        print("-" * 50)
        
        config = RS232Config(
            port=port,
            baud_rate=baud_rate,
            timeout=1.0
        )
        
        # Set up event callbacks
        self.rs232_manager.on_data_received = lambda data: print(f"RX: {repr(data)}")
        self.rs232_manager.on_error = lambda error: print(f"ERROR: {error}")
        
        if not self.rs232_manager.connect(config):
            print("Failed to connect to port")
            return
        
        print(f"Connected successfully! Status: {self.rs232_manager.status.value}")
        
        try:
            while True:
                command = input("\nTX> ").strip()
                
                if command.lower() == 'quit':
                    break
                elif command.lower() == 'status':
                    status = self.rs232_manager.get_port_status()
                    print(json.dumps(status, indent=2))
                elif command.lower() == 'flush':
                    self.rs232_manager.flush_buffers()
                    print("Buffers flushed")
                elif command:
                    if not command.endswith('\r\n'):
                        command += '\r\n'
                    
                    if self.rs232_manager.send_data(command):
                        print(f"Sent: {repr(command)}")
                        # Check for immediate response
                        time.sleep(0.1)
                        response = self.rs232_manager.read_data(timeout=0.5)
                        if response:
                            print(f"RX: {repr(response)}")
                    else:
                        print("Send failed")
                
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        
        finally:
            self.rs232_manager.disconnect()
            print("Disconnected")
    
    def profile_test(self, profile_name: str = "Generic"):
        """Test using a hardware profile"""
        
        print(f"\n=== Profile Test: {profile_name} ===")
        
        try:
            profile = self.profile_manager.get_profile(profile_name)
            print(f"Profile: {profile.name}")
            print(f"Port: {profile.port}")
            print(f"Baud Rate: {profile.baud_rate}")
            print(f"Protocol: {profile.protocol}")
            print("-" * 30)
            
            # Convert profile to RS232Config
            config = RS232Config(
                port=profile.port,
                baud_rate=profile.baud_rate,
                data_bits=profile.data_bits,
                parity=profile.parity,
                stop_bits=profile.stop_bits,
                timeout=profile.timeout
            )
            
            # Test connection
            result = self.rs232_manager.test_connection(config, "TEST\r\n")
            
            print(f"Connection Test: {'PASSED' if result.success else 'FAILED'}")
            if result.error_message:
                print(f"Error: {result.error_message}")
            if result.raw_response:
                print(f"Response: {repr(result.raw_response)}")
            
        except Exception as e:
            print(f"Profile test failed: {e}")
    
    def stress_test(self, port: str, baud_rate: int = 9600, duration: int = 30, message_interval: float = 1.0):
        """Stress test RS232 connection"""
        
        print(f"\n=== RS232 Stress Test ===")
        print(f"Port: {port}")
        print(f"Baud Rate: {baud_rate}")
        print(f"Duration: {duration} seconds")
        print(f"Message Interval: {message_interval} seconds")
        print("-" * 40)
        
        config = RS232Config(
            port=port,
            baud_rate=baud_rate,
            timeout=2.0
        )
        
        if not self.rs232_manager.connect(config):
            print("Failed to connect for stress test")
            return
        
        start_time = time.time()
        message_count = 0
        error_count = 0
        
        try:
            while (time.time() - start_time) < duration:
                message = f"STRESS_TEST_{message_count}\r\n"
                
                if self.rs232_manager.send_data(message):
                    message_count += 1
                    # Check for response
                    response = self.rs232_manager.read_data(timeout=0.5)
                    if response:
                        print(f"#{message_count}: TX={len(message)} bytes, RX={len(response)} bytes")
                    else:
                        print(f"#{message_count}: TX={len(message)} bytes, RX=0 bytes")
                else:
                    error_count += 1
                    print(f"Send error #{error_count}")
                
                time.sleep(message_interval)
        
        except KeyboardInterrupt:
            print("\nStress test interrupted")
        
        finally:
            elapsed = time.time() - start_time
            stats = self.rs232_manager.get_port_status()['statistics']
            
            print(f"\n=== Stress Test Results ===")
            print(f"Duration: {elapsed:.1f} seconds")
            print(f"Messages Sent: {message_count}")
            print(f"Send Errors: {error_count}")
            print(f"Total Bytes TX: {stats['bytes_sent']}")
            print(f"Total Bytes RX: {stats['bytes_received']}")
            print(f"Success Rate: {((message_count - error_count) / max(message_count, 1) * 100):.1f}%")
            
            self.rs232_manager.disconnect()
    
    def generate_report(self, output_file: str = "rs232_test_report.json"):
        """Generate test report"""
        
        report = {
            'test_timestamp': datetime.now().isoformat(),
            'system_info': {
                'platform': sys.platform,
                'python_version': sys.version
            },
            'available_ports': self.rs232_manager.get_available_ports(),
            'test_results': self.test_results
        }
        
        try:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Test report saved to: {output_file}")
        except Exception as e:
            print(f"Failed to save report: {e}")

def main():
    """Command line interface for RS232 testing"""
    
    parser = argparse.ArgumentParser(
        description="RS232 Test Utility for SCALE System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rs232_test_utility.py scan
  python rs232_test_utility.py test COM1
  python rs232_test_utility.py interactive COM1 19200
  python rs232_test_utility.py stress COM1 9600 60
  python rs232_test_utility.py profile Generic
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan for available ports')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test baud rates on a port')
    test_parser.add_argument('port', help='Serial port to test (e.g., COM1, /dev/ttyUSB0)')
    test_parser.add_argument('--message', default='SCALE_TEST\r\n', help='Test message to send')
    
    # Interactive command
    interactive_parser = subparsers.add_parser('interactive', help='Interactive communication test')
    interactive_parser.add_argument('port', help='Serial port')
    interactive_parser.add_argument('baud_rate', type=int, nargs='?', default=9600, help='Baud rate')
    
    # Profile command
    profile_parser = subparsers.add_parser('profile', help='Test using hardware profile')
    profile_parser.add_argument('profile_name', help='Profile name to test')
    
    # Stress command
    stress_parser = subparsers.add_parser('stress', help='Stress test connection')
    stress_parser.add_argument('port', help='Serial port')
    stress_parser.add_argument('baud_rate', type=int, nargs='?', default=9600, help='Baud rate')
    stress_parser.add_argument('--duration', type=int, default=30, help='Test duration in seconds')
    stress_parser.add_argument('--interval', type=float, default=1.0, help='Message interval in seconds')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    utility = RS232TestUtility()
    
    try:
        if args.command == 'scan':
            utility.scan_ports()
        
        elif args.command == 'test':
            utility.test_baud_rates(args.port, args.message)
        
        elif args.command == 'interactive':
            utility.interactive_test(args.port, args.baud_rate)
        
        elif args.command == 'profile':
            utility.profile_test(args.profile_name)
        
        elif args.command == 'stress':
            utility.stress_test(args.port, args.baud_rate, args.duration, args.interval)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
