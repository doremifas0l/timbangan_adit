#!/usr/bin/env python3
"""
Mock Serial Service for SCALE System Testing
Provides simulated serial communication using the weight simulator
"""

import time
import queue
import threading
from datetime import datetime
from typing import Dict, Optional, Callable, Any
import json
from dataclasses import dataclass
from enum import Enum

# Import the real serial structures
from ..hardware.serial_service import SerialStatus, WeightReading, SerialProfile
from .weight_simulator import get_weight_simulator, VehicleType
from ..core.config import DEFAULT_SETTINGS

class MockSerialService:
    """Mock serial service that provides simulated weight data"""
    
    def __init__(self, profile: SerialProfile = None):
        # Use default profile if none provided
        if profile is None:
            profile = SerialProfile(
                port="MOCK_PORT",
                baud_rate=9600,
                protocol="simulation"
            )
        
        self.profile = profile
        self.status = SerialStatus.DISCONNECTED
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.weight_simulator = get_weight_simulator()
        
        # Communication queues
        self.weight_queue = queue.Queue(maxsize=100)
        self.command_queue = queue.Queue()
        
        # Callbacks
        self.weight_callback: Optional[Callable] = None
        self.status_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
            'connection_time': None,
            'last_reading_time': None
        }
        
        print("\u2699\ufe0f Mock Serial Service initialized")
    
    def connect(self) -> bool:
        """Connect to simulated serial port"""
        try:
            if self.status == SerialStatus.CONNECTED:
                return True
            
            print(f"\u2699\ufe0f Connecting to simulated serial port: {self.profile.port}")
            self.status = SerialStatus.CONNECTING
            
            if self.status_callback:
                self.status_callback(self.status)
            
            # Simulate connection delay
            time.sleep(0.5)
            
            self.status = SerialStatus.CONNECTED
            self.stats['connection_time'] = datetime.utcnow().isoformat()
            
            print(f"\u2705 Mock serial connection established")
            
            if self.status_callback:
                self.status_callback(self.status)
            
            return True
            
        except Exception as e:
            print(f"\u274c Mock serial connection failed: {e}")
            self.status = SerialStatus.ERROR
            self.stats['errors'] += 1
            
            if self.error_callback:
                self.error_callback(str(e))
            if self.status_callback:
                self.status_callback(self.status)
            
            return False
    
    def disconnect(self):
        """Disconnect from simulated serial port"""
        if self.status == SerialStatus.DISCONNECTED:
            return
        
        print("\u2699\ufe0f Disconnecting mock serial service...")
        
        self.stop_monitoring()
        self.status = SerialStatus.DISCONNECTED
        
        if self.status_callback:
            self.status_callback(self.status)
        
        print("\u2705 Mock serial service disconnected")
    
    def start_monitoring(self) -> bool:
        """Start monitoring simulated weight data"""
        if self.status != SerialStatus.CONNECTED:
            print("\u274c Cannot start monitoring - not connected")
            return False
        
        if self.is_running:
            print("\u2699\ufe0f Monitoring already active")
            return True
        
        self.is_running = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        
        print("\u2699\ufe0f Mock weight monitoring started")
        return True
    
    def stop_monitoring(self):
        """Stop monitoring weight data"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        print("\u2699\ufe0f Mock weight monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop for simulated weight data"""
        print("\u2699\ufe0f Mock monitoring loop started")
        
        while self.is_running:
            try:
                # Get simulated weight reading
                sim_reading = self.weight_simulator.get_weight_reading()
                
                # Convert to WeightReading format
                weight_reading = WeightReading(
                    weight=sim_reading.gross_weight,
                    stable=sim_reading.is_stable,
                    unit="KG",
                    timestamp=sim_reading.timestamp.isoformat(),
                    raw_data=f"MOCK:{sim_reading.gross_weight:.1f},{'ST' if sim_reading.is_stable else 'US'},KG"
                )
                
                # Add to queue
                if not self.weight_queue.full():
                    self.weight_queue.put(weight_reading)
                    self.stats['messages_received'] += 1
                    self.stats['last_reading_time'] = datetime.utcnow().isoformat()
                    
                    # Call callback if registered
                    if self.weight_callback:
                        self.weight_callback(weight_reading)
                
                # Handle commands
                try:
                    command = self.command_queue.get_nowait()
                    self._handle_command(command)
                except queue.Empty:
                    pass
                
                # Simulate reading frequency
                time.sleep(0.1)  # 10 readings per second
                
            except Exception as e:
                print(f"\u274c Mock monitoring error: {e}")
                self.stats['errors'] += 1
                time.sleep(1.0)
        
        print("\u2699\ufe0f Mock monitoring loop stopped")
    
    def _handle_command(self, command: Dict[str, Any]):
        """Handle commands for simulation control"""
        cmd_type = command.get('type')
        
        if cmd_type == 'start_vehicle_simulation':
            vehicle_type = command.get('vehicle_type', 'heavy_truck')
            vehicle_id = command.get('vehicle_id')
            cargo_percentage = command.get('cargo_percentage', 0.7)
            
            try:
                vtype = VehicleType(vehicle_type)
                self.weight_simulator.start_simulation(vtype, vehicle_id, cargo_percentage)
                print(f"\u2699\ufe0f Started vehicle simulation: {vehicle_type} ({vehicle_id})")
            except Exception as e:
                print(f"\u274c Failed to start vehicle simulation: {e}")
        
        elif cmd_type == 'stop_vehicle_simulation':
            self.weight_simulator.stop_simulation()
            print("\u2699\ufe0f Stopped vehicle simulation")
        
        elif cmd_type == 'simulate_movement':
            movement = command.get('movement', 'settling')
            self.weight_simulator.simulate_vehicle_movement(movement)
            print(f"\u2699\ufe0f Simulated vehicle movement: {movement}")
        
        elif cmd_type == 'test_scenario':
            scenario = command.get('scenario', 'heavy_freight')
            try:
                config = self.weight_simulator.generate_test_scenario(scenario)
                print(f"\u2699\ufe0f Started test scenario: {scenario} - {config['description']}")
            except Exception as e:
                print(f"\u274c Failed to start test scenario: {e}")
    
    def send_command(self, command: Dict[str, Any]):
        """Send a command to the mock serial service"""
        self.command_queue.put(command)
        self.stats['messages_sent'] += 1
    
    def get_latest_reading(self) -> Optional[WeightReading]:
        """Get the latest weight reading from the queue"""
        try:
            return self.weight_queue.get_nowait()
        except queue.Empty:
            return None
    
    def get_all_readings(self) -> list:
        """Get all available weight readings"""
        readings = []
        while not self.weight_queue.empty():
            try:
                readings.append(self.weight_queue.get_nowait())
            except queue.Empty:
                break
        return readings
    
    def clear_queue(self):
        """Clear the weight reading queue"""
        with self.weight_queue.mutex:
            self.weight_queue.queue.clear()
    
    def set_weight_callback(self, callback: Callable):
        """Set callback for weight readings"""
        self.weight_callback = callback
    
    def set_status_callback(self, callback: Callable):
        """Set callback for status changes"""
        self.status_callback = callback
    
    def set_error_callback(self, callback: Callable):
        """Set callback for errors"""
        self.error_callback = callback
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status"""
        sim_status = self.weight_simulator.get_simulation_status()
        
        return {
            'serial_status': self.status.value,
            'is_monitoring': self.is_running,
            'profile': {
                'port': self.profile.port,
                'baud_rate': self.profile.baud_rate,
                'protocol': self.profile.protocol
            },
            'queue_size': self.weight_queue.qsize(),
            'statistics': self.stats,
            'simulation': sim_status
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get communication statistics"""
        return self.stats.copy()
    
    # Convenience methods for test scenarios
    def start_test_scenario(self, scenario: str) -> bool:
        """Start a predefined test scenario"""
        try:
            self.send_command({
                'type': 'test_scenario',
                'scenario': scenario
            })
            return True
        except Exception as e:
            print(f"\u274c Failed to start test scenario: {e}")
            return False
    
    def simulate_vehicle_entry(self, vehicle_type: str = "heavy_truck", 
                               vehicle_id: str = None, cargo_percentage: float = 0.7):
        """Simulate a vehicle entering the scale"""
        self.send_command({
            'type': 'start_vehicle_simulation',
            'vehicle_type': vehicle_type,
            'vehicle_id': vehicle_id,
            'cargo_percentage': cargo_percentage
        })
        
        # Simulate settling
        time.sleep(0.1)
        self.send_command({
            'type': 'simulate_movement',
            'movement': 'settling'
        })
    
    def simulate_vehicle_exit(self):
        """Simulate a vehicle leaving the scale"""
        self.send_command({
            'type': 'simulate_movement',
            'movement': 'leaving'
        })
        
        time.sleep(1.0)  # Allow weight to go to zero
        
        self.send_command({
            'type': 'stop_vehicle_simulation'
        })

# Factory function to create appropriate serial service
def create_serial_service(mock_mode: bool = False, profile: SerialProfile = None):
    """Create either real or mock serial service based on mode"""
    
    if mock_mode or DEFAULT_SETTINGS.get('test_mode_enabled', False):
        print("\u2699\ufe0f Creating Mock Serial Service for testing")
        return MockSerialService(profile)
    else:
        # Import and create real serial service
        from ..hardware.serial_service import SerialService
        print("\u2699\ufe0f Creating Real Serial Service")
        return SerialService(profile)

if __name__ == "__main__":
    # Demo the mock serial service
    print("Mock Serial Service Demo")
    print("="*50)
    
    # Create mock service
    mock_service = MockSerialService()
    
    # Set up callbacks
    def on_weight(reading):
        stable = "STABLE" if reading.stable else "UNSTABLE"
        print(f"Weight: {reading.weight:.1f} kg ({stable})")
    
    def on_status(status):
        print(f"Status: {status.value}")
    
    mock_service.set_weight_callback(on_weight)
    mock_service.set_status_callback(on_status)
    
    # Connect and start monitoring
    if mock_service.connect():
        mock_service.start_monitoring()
        
        # Start a test scenario
        print("\nStarting heavy freight scenario...")
        mock_service.start_test_scenario('heavy_freight')
        
        # Let it run for a few seconds
        time.sleep(5)
        
        print("\nSimulating vehicle exit...")
        mock_service.simulate_vehicle_exit()
        
        time.sleep(2)
        
        # Stop and disconnect
        mock_service.disconnect()
        
        # Show statistics
        stats = mock_service.get_statistics()
        print(f"\nStatistics:")
        print(f"  Messages received: {stats['messages_received']}")
        print(f"  Messages sent: {stats['messages_sent']}")
        print(f"  Errors: {stats['errors']}")
