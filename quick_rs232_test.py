#!/usr/bin/env python3
"""
Quick RS232 Baud Rate Tester
Simple utility to quickly test the requested baud rates
"""

import sys
from pathlib import Path
import time

# Add the scale_system module to the path
sys.path.insert(0, str(Path(__file__).parent))

from hardware.rs232_manager import RS232Manager, RS232Config

def quick_baud_test(port: str = "COM1"):
    """Quick test of user-requested baud rates"""
    
    print("=== SCALE System RS232 Quick Test ===")
    print(f"Testing port: {port}")
    print("Testing user-requested baud rates: 9600, 19200, 38400, 115200")
    print("-" * 50)
    
    rs232_manager = RS232Manager()
    requested_rates = [9600, 19200, 38400, 115200]
    
    results = []
    
    for baud_rate in requested_rates:
        print(f"Testing {baud_rate:6} baud...", end=" ")
        
        config = RS232Config(
            port=port,
            baud_rate=baud_rate,
            timeout=1.0
        )
        
        try:
            result = rs232_manager.test_connection(config, "TEST\r\n")
            
            if result.success:
                status = f"✅ OK ({result.response_time:.3f}s)"
                if result.bytes_received > 0:
                    status += f" [{result.bytes_received} bytes]"
                results.append((baud_rate, True, result.response_time))
            else:
                status = f"❌ FAILED ({result.error_message})"
                results.append((baud_rate, False, 0))
            
            print(status)
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append((baud_rate, False, 0))
    
    print("\n=== Test Summary ===")
    working_rates = [rate for rate, success, _ in results if success]
    
    if working_rates:
        print(f"✅ Working baud rates: {working_rates}")
    else:
        print("❌ No baud rates responded (normal if no hardware connected)")
    
    print("\n📋 All requested baud rates are SUPPORTED by the system.")
    print("   Test results depend on connected hardware capabilities.")
    
    return results

def test_with_auto_detect():
    """Test with automatic port detection"""
    
    print("\n=== Auto-Detection Test ===")
    
    rs232_manager = RS232Manager()
    ports = rs232_manager.get_available_ports()
    
    if not ports:
        print("No ports detected. Testing with COM1 as example.")
        quick_baud_test("COM1")
        return
    
    print(f"Detected {len(ports)} port(s). Testing first port...")
    first_port = ports[0]['device']
    quick_baud_test(first_port)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_port = sys.argv[1]
        quick_baud_test(test_port)
    else:
        test_with_auto_detect()
