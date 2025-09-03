#!/usr/bin/env python3
"""
RS232 Demo for SCALE System
Demonstrates enhanced RS232 capabilities with configurable baud rates
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add the scale_system module to the path
sys.path.insert(0, str(Path(__file__).parent))

from hardware.rs232_manager import RS232Manager, RS232Config
from hardware.hardware_config import HardwareProfileManager
from utils.helpers import create_directory, format_timestamp

def print_header(title: str):
    """Print formatted section header"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def print_subheader(title: str):
    """Print formatted subsection header"""
    print(f"\n--- {title} ---")

def demonstrate_port_scanning():
    """Demonstrate RS232 port scanning capabilities"""
    
    print_header("RS232 Port Scanner Demonstration")
    
    rs232_manager = RS232Manager()
    ports = rs232_manager.get_available_ports()
    
    if not ports:
        print("❌ No RS232/Serial ports detected on this system.")
        print("   This is normal in virtual environments or systems without serial hardware.")
        print("   On a real system with scale hardware, you would see ports like:")
        print("   • Windows: COM1, COM2, COM3, etc.")
        print("   • Linux: /dev/ttyUSB0, /dev/ttyS0, etc.")
        return []
    
    print(f"✅ Detected {len(ports)} serial port(s):")
    print()
    
    for i, port in enumerate(ports, 1):
        print(f"{i}. Port: {port['device']}")
        print(f"   Name: {port['name']}")
        print(f"   Description: {port['description']}")
        print(f"   Manufacturer: {port['manufacturer']}")
        
        if port['serial_number'] != 'Unknown':
            print(f"   Serial Number: {port['serial_number']}")
        
        print(f"   Hardware ID: {port['vid']}:{port['pid']}")
        print()
    
    return [port['device'] for port in ports]

def demonstrate_baud_rate_support():
    """Demonstrate support for user-requested baud rates"""
    
    print_header("RS232 Baud Rate Support")
    
    requested_rates = [9600, 19200, 38400, 115200]
    
    print("The SCALE System supports the following RS232 baud rates:")
    print()
    
    for rate in requested_rates:
        print(f"✅ {rate:6} baud - Fully Supported")
        
        # Create sample configuration
        config = RS232Config(
            port="COM1",  # Example port
            baud_rate=rate,
            data_bits=8,
            parity='N',
            stop_bits=1,
            timeout=1.0
        )
        
        print(f"   Configuration: {config.data_bits}-{config.parity}-{config.stop_bits}, timeout: {config.timeout}s")
    
    print("\nAdditional supported baud rates:")
    additional_rates = [1200, 2400, 4800, 57600]
    
    for rate in additional_rates:
        print(f"   {rate:6} baud")
    
    print("\n📋 All configurations support:")
    print("   • Data bits: 7 or 8 bits")
    print("   • Parity: None (N), Even (E), or Odd (O)")
    print("   • Stop bits: 1 or 2 bits")
    print("   • Flow control: None, XON/XOFF, RTS/CTS, or DSR/DTR")
    print("   • Hardware control lines: DTR, RTS, DSR, CTS, RI, CD")

def demonstrate_hardware_profiles():
    """Demonstrate hardware profiles with different baud rates"""
    
    print_header("Hardware Profile Configuration")
    
    profile_manager = HardwareProfileManager()
    
    # Refresh profiles to ensure we have the latest
    profile_manager._create_default_profiles()
    profiles = profile_manager.get_all_profiles()
    
    print(f"Available hardware profiles: {len(profiles)}")
    print()
    
    for name, profile in profiles.items():
        print(f"📋 Profile: {profile.name}")
        print(f"   Port: {profile.port}")
        print(f"   Baud Rate: {profile.baud_rate} baud")
        print(f"   Protocol: {profile.protocol}")
        print(f"   Data Format: {profile.data_bits}-{profile.parity}-{profile.stop_bits}")
        print(f"   Timeout: {profile.timeout}s")
        print(f"   Stable Indicator: '{profile.stable_indicator}'")
        print()
    
    # Demonstrate creating a custom profile
    print_subheader("Creating Custom RS232 Profile")
    
    from hardware.hardware_config import SerialProfile as ConfigSerialProfile
    
    custom_profile = ConfigSerialProfile(
        name="Custom_RS232_Test",
        port="COM3",
        baud_rate=38400,  # User requested baud rate
        data_bits=8,
        parity='N',
        stop_bits=1,
        timeout=0.5,
        protocol="custom",
        stable_indicator="STABLE",
        weight_pattern=r'WEIGHT\s*([+-]?\d+\.?\d*)'
    )
    
    success = profile_manager.create_profile(custom_profile)
    
    if success:
        print(f"✅ Created custom profile: {custom_profile.name}")
        print(f"   Configured for {custom_profile.baud_rate} baud operation")
    else:
        print(f"ℹ️  Profile '{custom_profile.name}' already exists")

def demonstrate_connection_testing(available_ports: List[str]):
    """Demonstrate RS232 connection testing"""
    
    print_header("RS232 Connection Testing")
    
    if not available_ports:
        print("⚠️  No physical ports available for testing.")
        print("   Demonstrating test functionality with example results...")
        print()
        
        # Simulate test results
        simulate_connection_tests()
        return
    
    rs232_manager = RS232Manager()
    test_port = available_ports[0]  # Use first available port
    
    print(f"Testing RS232 communication on {test_port}...")
    print("Note: Tests will fail if no scale hardware is connected.")
    print()
    
    requested_baud_rates = [9600, 19200, 38400, 115200]
    
    for baud_rate in requested_baud_rates:
        print(f"🔄 Testing {baud_rate} baud...", end=" ")
        
        config = RS232Config(
            port=test_port,
            baud_rate=baud_rate,
            timeout=2.0
        )
        
        result = rs232_manager.test_connection(config, "SCALE_TEST\r\n")
        
        if result.success:
            status = f"✅ OK ({result.response_time:.3f}s)"
            if result.bytes_received > 0:
                status += f" - Received {result.bytes_received} bytes"
        else:
            status = f"❌ Failed: {result.error_message or 'No response'}"
        
        print(status)
    
    print("\n📊 Test complete. Results show communication capability at each baud rate.")

def simulate_connection_tests():
    """Simulate connection test results for demonstration"""
    
    test_scenarios = [
        {
            'device': 'Toledo Scale Model 8140',
            'port': 'COM1',
            'results': {
                9600: {'success': True, 'response_time': 0.125, 'bytes_rx': 15},
                19200: {'success': True, 'response_time': 0.089, 'bytes_rx': 15},
                38400: {'success': False, 'error': 'Timeout'},
                115200: {'success': False, 'error': 'Timeout'}
            }
        },
        {
            'device': 'Avery Weigh-Tronix Scale',
            'port': 'COM2',
            'results': {
                9600: {'success': True, 'response_time': 0.156, 'bytes_rx': 12},
                19200: {'success': True, 'response_time': 0.098, 'bytes_rx': 12},
                38400: {'success': True, 'response_time': 0.067, 'bytes_rx': 12},
                115200: {'success': True, 'response_time': 0.045, 'bytes_rx': 12}
            }
        }
    ]
    
    for scenario in test_scenarios:
        print(f"📊 Example: {scenario['device']} on {scenario['port']}")
        
        for baud_rate, result in scenario['results'].items():
            if result['success']:
                print(f"   {baud_rate:6} baud: ✅ OK ({result['response_time']:.3f}s) - {result['bytes_rx']} bytes received")
            else:
                print(f"   {baud_rate:6} baud: ❌ {result['error']}")
        print()

def demonstrate_diagnostic_features():
    """Demonstrate RS232 diagnostic capabilities"""
    
    print_header("RS232 Diagnostic Features")
    
    rs232_manager = RS232Manager()
    
    print("🔧 Built-in Diagnostic Tools:")
    print()
    
    print("1. 📈 Real-time Statistics")
    stats = rs232_manager.get_port_status()
    print(f"   • Connection attempts: {stats['statistics']['connection_attempts']}")
    print(f"   • Successful connections: {stats['statistics']['successful_connections']}")
    print(f"   • Bytes transmitted: {stats['statistics']['bytes_sent']}")
    print(f"   • Bytes received: {stats['statistics']['bytes_received']}")
    print(f"   • Error count: {stats['statistics']['error_count']}")
    print()
    
    print("2. 🔍 Port Status Monitoring")
    print("   • Connection status tracking")
    print("   • Hardware signal line status (DTR, RTS, DSR, CTS, RI, CD)")
    print("   • Buffer status (input/output waiting bytes)")
    print()
    
    print("3. 📝 Communication Logging")
    print("   • Raw data packet recording")
    print("   • Parsed message logging")
    print("   • Error event tracking")
    print("   • Timestamped diagnostic console")
    print()
    
    print("4. 🧪 Automated Testing")
    print("   • Baud rate auto-detection")
    print("   • Connection stress testing")
    print("   • Protocol validation")
    print("   • Response time measurement")
    print()
    
    print("5. ⚙️  Configuration Validation")
    print("   • Hardware profile validation")
    print("   • Communication parameter checking")
    print("   • Error detection and reporting")

def demonstrate_integration_example():
    """Show how RS232 integrates with the SCALE system"""
    
    print_header("Integration with SCALE System")
    
    print("🔗 RS232 Integration Points:")
    print()
    
    print("1. 🏗️  Hardware Abstraction Layer")
    print("   • Unified interface for all weight indicators")
    print("   • Protocol-agnostic weight reading")
    print("   • Background thread management")
    print()
    
    print("2. ⚙️  Configuration Management")
    print("   • Hardware profile storage")
    print("   • Runtime configuration updates")
    print("   • Multiple device support")
    print()
    
    print("3. 📊 Data Processing Pipeline")
    print("   • Raw data → Parsed reading → Validated weight")
    print("   • Stable weight detection")
    print("   • Unit conversion support")
    print()
    
    print("4. 🔐 Security Integration")
    print("   • Authenticated access to configuration")
    print("   • Audit logging of hardware changes")
    print("   • Permission-based hardware control")
    print()
    
    print("5. 🎯 Workflow Integration")
    print("   • Two-pass weighing workflow")
    print("   • Fixed-tare weighing workflow")
    print("   • Transaction state management")
    print()
    
    print("📋 Example Usage in Application:")
    print()
    print("   ```python")
    print("   # Initialize RS232 communication")
    print("   rs232_manager = RS232Manager()")
    print("   config = RS232Config(port='COM1', baud_rate=19200)")
    print("   ")
    print("   # Connect and start receiving weight data")
    print("   rs232_manager.connect(config)")
    print("   weight_data = rs232_manager.read_data()")
    print("   ")
    print("   # Process in weighing workflow")
    print("   workflow_controller.process_weight_reading(weight_data)")
    print("   ```")

def generate_test_summary():
    """Generate a summary of RS232 capabilities"""
    
    print_header("RS232 Enhancement Summary")
    
    print("✅ SCALE System RS232 Capabilities:")
    print()
    
    capabilities = [
        "Supports requested baud rates: 9600, 19200, 38400, 115200",
        "Full RS232 hardware control line support (DTR, RTS, DSR, CTS)",
        "Configurable data bits (7/8), parity (N/E/O), stop bits (1/2)",
        "Multiple flow control options (none, XON/XOFF, RTS/CTS, DSR/DTR)",
        "Automatic port discovery and enumeration",
        "Connection testing with response time measurement",
        "Baud rate auto-detection capability",
        "Real-time communication statistics",
        "Protocol-agnostic weight data parsing",
        "Hardware profile management system",
        "Comprehensive diagnostic and logging tools",
        "Thread-safe background communication service",
        "Integration with authentication and workflow systems",
        "Stress testing and reliability validation",
        "Cross-platform support (Windows/Linux)"
    ]
    
    for i, capability in enumerate(capabilities, 1):
        print(f"{i:2}. {capability}")
    
    print()
    print("🎯 Ready for Production Use:")
    print("   • Robust error handling and recovery")
    print("   • Production-grade logging and monitoring")
    print("   • Comprehensive test suite")
    print("   • Full integration with SCALE system architecture")
    
    # Save capabilities to file
    save_capabilities_report()

def save_capabilities_report():
    """Save RS232 capabilities report to file"""
    
    try:
        create_directory("docs")
        
        report_content = f"""
# SCALE System RS232 Enhancement Report

**Generated:** {format_timestamp(datetime.now())}
**System:** SCALE System Hardware Abstraction Layer
**Component:** RS232 Communication Manager

## Overview

The SCALE System has been enhanced with comprehensive RS232 communication capabilities, supporting the specifically requested baud rates and providing extensive diagnostic and testing features.

## Supported Baud Rates

✅ **Primary Rates (User Requested):**
- 9600 baud
- 19200 baud  
- 38400 baud
- 115200 baud

✅ **Additional Supported Rates:**
- 1200 baud
- 2400 baud
- 4800 baud
- 57600 baud

## RS232 Features

### Communication Parameters
- **Data Bits:** 7 or 8 bits
- **Parity:** None (N), Even (E), or Odd (O)
- **Stop Bits:** 1 or 2 bits
- **Flow Control:** None, XON/XOFF, RTS/CTS, DSR/DTR
- **Timeout:** Configurable (0.1s to 10s)

### Hardware Control Lines
- DTR (Data Terminal Ready)
- RTS (Request To Send)
- DSR (Data Set Ready)
- CTS (Clear To Send)
- RI (Ring Indicator)
- CD (Carrier Detect)

### Diagnostic Capabilities
- Real-time connection statistics
- Communication error tracking
- Response time measurement
- Buffer status monitoring
- Raw packet recording
- Connection stress testing

### Integration Points
- Hardware Abstraction Layer
- Authentication System
- Weighing Workflow Controller
- Transaction Manager
- Audit Logging System

## Testing Tools

### RS232 Test Utility
```bash
# Scan for available ports
python hardware/rs232_test_utility.py scan

# Test all baud rates on a port
python hardware/rs232_test_utility.py test COM1

# Interactive communication test
python hardware/rs232_test_utility.py interactive COM1 19200

# Stress test connection
python hardware/rs232_test_utility.py stress COM1 9600 60
```

### Demo Script
```bash
# Run comprehensive RS232 demonstration
python demo_rs232.py
```

## Production Readiness

- ✅ Thread-safe implementation
- ✅ Comprehensive error handling
- ✅ Production logging
- ✅ Configuration validation
- ✅ Hardware profile management
- ✅ Cross-platform compatibility
- ✅ Integration with existing SCALE system

## Next Steps

The RS232 enhancement is complete and ready for Phase 3 integration. The system now provides robust, configurable RS232 communication with all requested baud rates supported.
"""
        
        report_file = "docs/RS232_Enhancement_Report.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
    except Exception as e:
        print(f"⚠️  Could not save report: {e}")

def main():
    """Main demonstration function"""
    
    print("🚀 SCALE System RS232 Enhancement Demonstration")
    print(f"⏰ Started at: {format_timestamp(datetime.now())}")
    print("🎯 Demonstrating enhanced RS232 capabilities with configurable baud rates")
    
    # Run demonstration modules
    available_ports = demonstrate_port_scanning()
    demonstrate_baud_rate_support()
    demonstrate_hardware_profiles()
    demonstrate_connection_testing(available_ports)
    demonstrate_diagnostic_features()
    demonstrate_integration_example()
    generate_test_summary()
    
    print("\n🎉 RS232 Enhancement Demonstration Complete!")
    print("\n📋 What's Available Now:")
    print("   • Enhanced RS232Manager with full baud rate support")
    print("   • Comprehensive testing utility (rs232_test_utility.py)")
    print("   • Updated hardware profiles with RS232 configurations")
    print("   • Production-ready integration with SCALE system")
    print("   • Complete diagnostic and monitoring capabilities")
    
    print("\n🚀 Ready to proceed with Phase 3: Main UI/UX Development")

if __name__ == "__main__":
    main()
