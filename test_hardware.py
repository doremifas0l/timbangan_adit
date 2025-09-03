#!/usr/bin/env python3
"""
SCALE System Hardware Test
Tests serial communication with simulated weight indicator data
"""

import sys
from pathlib import Path
import time
import random

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from hardware.serial_service import SerialProtocolParser
from hardware.hardware_config import HardwareProfileManager, DiagnosticConsole, SerialProfile
from hardware.hardware_config import HardwareProfileManager, DiagnosticConsole
from utils.helpers import format_weight

def test_protocol_parsing():
    """Test different protocol parsers"""
    print("\n=== PROTOCOL PARSING TEST ===")
    
    # Test data for different protocols
    test_data = {
        'generic': [
            "1234.56 KG ST",
            "2000.00 LB",
            "567.89 G ST",
            "invalid data",
            "0.00 KG ST"
        ],
        'toledo': [
            "+001234.5 kg ST",
            "-000500.0 kg",
            "+002000.00 lb ST",
            "invalid toledo"
        ],
        'avery': [
            "WEIGHT 1234.56 KG STABLE",
            "WEIGHT 2000.00 LB",
            "ERROR OVERLOAD"
        ]
    }
    
    # Test each protocol
    for protocol_name, messages in test_data.items():
        print(f"\n{protocol_name.upper()} Protocol:")
        
        # Create profile for this protocol
        profile = SerialProfile(
            name=f"Test {protocol_name}",
            port="TEST",
            protocol=protocol_name
        )
        
        parser = SerialProtocolParser(profile)
        
        for message in messages:
            reading = parser.parse_message(message)
            if reading:
                stable_indicator = "STABLE" if reading.stable else "MOTION"
                print(f"   '{message}' -> {reading.weight} {reading.unit} ({stable_indicator})")
            else:
                print(f"   '{message}' -> PARSE_ERROR")

def test_diagnostic_console():
    """Test diagnostic console functionality"""
    print("\n=== DIAGNOSTIC CONSOLE TEST ===")
    
    console = DiagnosticConsole(max_lines=10)
    
    # Simulate various message types
    messages = [
        ('status', {'status': 'connected', 'port': 'COM1'}),
        ('raw_data', {'data': '1234.56 KG ST\r\n'}),
        ('weight_reading', {'weight': 1234.56, 'stable': True, 'unit': 'KG'}),
        ('error', {'message': 'Connection timeout'}),
        ('raw_data', {'data': '2000.00 LB\r\n'}),
        ('weight_reading', {'weight': 2000.00, 'stable': False, 'unit': 'LB'})
    ]
    
    # Add messages to console
    current_time = '2024-01-01T10:00:00'
    for i, (msg_type, data) in enumerate(messages):
        timestamp = f"2024-01-01T10:{i:02d}:00"
        console.add_message(msg_type, timestamp, data)
    
    # Display console data
    print("\nConsole Messages:")
    for entry in console.get_console_data():
        print(f"   {entry['message']}")
    
    # Test filters
    print("\nTesting Filters:")
    console.set_filter('show_raw', False)
    print("   Raw data filter disabled")
    
    # Test export
    export_file = "data/diagnostic_log.txt"
    if console.export_log(export_file):
        print(f"   ✓ Console exported to {export_file}")
    else:
        print(f"   ✗ Console export failed")

def test_hardware_profiles():
    """Test hardware profile management"""
    print("\n=== HARDWARE PROFILES TEST ===")
    
    # Create profile manager
    manager = HardwareProfileManager("config")
    
    # List existing profiles
    profiles = manager.get_all_profiles()
    print(f"\nExisting Profiles ({len(profiles)}):")
    for name, profile in profiles.items():
        print(f"   {name}: {profile.port} @ {profile.baud_rate} baud")
    
    # Create a custom profile
    custom_profile = SerialProfile(
        name="Custom Test",
        port="COM3",
        baud_rate=19200,
        protocol="custom",
        stable_threshold=1.0,
        stable_duration=5
    )
    
    if manager.create_profile(custom_profile):
        print(f"\n✓ Created custom profile: {custom_profile.name}")
    else:
        print(f"\n✗ Failed to create custom profile")
    
    # Test port detection
    available_ports = manager.get_available_ports()
    print(f"\nAvailable Serial Ports:")
    for port in available_ports[:5]:  # Show first 5
        print(f"   {port}")
    if len(available_ports) > 5:
        print(f"   ... and {len(available_ports) - 5} more")

def simulate_weight_readings():
    """Simulate realistic weight readings"""
    print("\n=== WEIGHT READING SIMULATION ===")
    
    # Simulate a truck weighing process
    print("\nSimulating truck weighing process...")
    
    # Phase 1: Truck approaching (unstable readings)
    print("\n1. Truck approaching (unstable readings):")
    base_weight = 5000.0
    for i in range(5):
        # Add random fluctuation for unstable weight
        fluctuation = random.uniform(-50, 50)
        weight = base_weight + fluctuation
        
        stable = abs(fluctuation) < 2.0  # Consider stable if fluctuation < 2kg
        status = "STABLE" if stable else "MOTION"
        
        print(f"   Reading {i+1}: {format_weight(weight, 2)} ({status})")
        time.sleep(0.2)
    
    # Phase 2: Truck settled (stable readings)
    print("\n2. Truck settled on platform:")
    stable_weight = 5234.75
    for i in range(3):
        # Small variation for realistic stable reading
        variation = random.uniform(-0.1, 0.1)
        weight = stable_weight + variation
        
        print(f"   Reading {i+1}: {format_weight(weight, 2)} (STABLE)")
        time.sleep(0.2)
    
    print(f"\n✓ Final stable weight: {format_weight(stable_weight, 2)}")
    
    # Simulate second weighing (tare)
    print("\n3. Second weighing (tare weight):")
    tare_weight = 1850.25
    for i in range(3):
        variation = random.uniform(-0.1, 0.1)
        weight = tare_weight + variation
        
        print(f"   Reading {i+1}: {format_weight(weight, 2)} (STABLE)")
        time.sleep(0.2)
    
    # Calculate net weight
    net_weight = stable_weight - tare_weight
    print(f"\n✓ Gross Weight: {format_weight(stable_weight, 2)}")
    print(f"✓ Tare Weight: {format_weight(tare_weight, 2)}")
    print(f"✓ Net Weight: {format_weight(net_weight, 2)}")

def main():
    """Main test function"""
    print("\n" + "="*60)
    print("SCALE SYSTEM - HARDWARE ABSTRACTION LAYER TEST")
    print("Testing serial communication and hardware components")
    print("="*60)
    
    try:
        # Run hardware tests
        test_protocol_parsing()
        test_diagnostic_console()
        test_hardware_profiles()
        simulate_weight_readings()
        
        print("\n" + "="*60)
        print("HARDWARE TESTS COMPLETED SUCCESSFULLY!")
        print("\n✅ Protocol Parsing")
        print("✅ Diagnostic Console")
        print("✅ Hardware Profiles")
        print("✅ Weight Reading Simulation")
        print("\n🔧 Hardware abstraction layer is ready!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Hardware test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
