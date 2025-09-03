#!/usr/bin/env python3
"""
Weight Simulation System for SCALE System
Provides realistic weight data simulation for testing and demo purposes
"""

import random
import time
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

class VehicleType(Enum):
    """Types of vehicles for simulation"""
    LIGHT_TRUCK = "light_truck"
    HEAVY_TRUCK = "heavy_truck"
    TRAILER = "trailer"
    BUS = "bus"
    PICKUP = "pickup"
    VAN = "van"

@dataclass
class VehicleProfile:
    """Vehicle profile for weight simulation"""
    vehicle_type: VehicleType
    empty_weight_range: Tuple[float, float]  # Min, Max empty weight
    max_cargo_weight: float
    weight_variance: float  # Random variance percentage
    stability_factor: float  # How stable the weight readings are

@dataclass
class SimulatedWeight:
    """Represents a simulated weight reading"""
    gross_weight: float
    is_stable: bool
    noise_level: float
    timestamp: datetime
    vehicle_id: Optional[str] = None
    measurement_type: str = "gross"  # gross, tare, net

class WeightSimulator:
    """Simulates realistic weight measurements for testing"""
    
    def __init__(self):
        self.vehicle_profiles = {
            VehicleType.LIGHT_TRUCK: VehicleProfile(
                vehicle_type=VehicleType.LIGHT_TRUCK,
                empty_weight_range=(3000, 7000),
                max_cargo_weight=15000,
                weight_variance=0.02,  # 2% variance
                stability_factor=0.95
            ),
            VehicleType.HEAVY_TRUCK: VehicleProfile(
                vehicle_type=VehicleType.HEAVY_TRUCK,
                empty_weight_range=(15000, 25000),
                max_cargo_weight=50000,
                weight_variance=0.03,  # 3% variance
                stability_factor=0.90
            ),
            VehicleType.TRAILER: VehicleProfile(
                vehicle_type=VehicleType.TRAILER,
                empty_weight_range=(25000, 40000),
                max_cargo_weight=80000,
                weight_variance=0.04,  # 4% variance
                stability_factor=0.85
            ),
            VehicleType.PICKUP: VehicleProfile(
                vehicle_type=VehicleType.PICKUP,
                empty_weight_range=(2000, 4000),
                max_cargo_weight=5000,
                weight_variance=0.015,  # 1.5% variance
                stability_factor=0.98
            )
        }
        
        self.current_vehicle: Optional[Dict[str, Any]] = None
        self.simulation_active = False
        self.base_weight = 0.0
        self.target_weight = 0.0
        self.weight_trend = 0.0
        self.stability_counter = 0
        self.measurement_history: List[SimulatedWeight] = []
        
        # Environmental factors
        self.wind_factor = 0.0
        self.vibration_factor = 0.0
        self.temperature_drift = 0.0
        
    def start_simulation(self, vehicle_type: VehicleType = VehicleType.HEAVY_TRUCK,
                        vehicle_id: str = None, cargo_percentage: float = 0.7) -> Dict[str, Any]:
        """Start weight simulation for a vehicle"""
        
        if vehicle_id is None:
            vehicle_id = f"VEH-{random.randint(1000, 9999)}"
        
        profile = self.vehicle_profiles[vehicle_type]
        
        # Calculate vehicle weights
        empty_weight = random.uniform(*profile.empty_weight_range)
        cargo_weight = profile.max_cargo_weight * cargo_percentage
        total_weight = empty_weight + cargo_weight
        
        # Add some realistic variance
        variance = total_weight * profile.weight_variance * random.uniform(-1, 1)
        total_weight += variance
        
        self.current_vehicle = {
            'id': vehicle_id,
            'type': vehicle_type,
            'empty_weight': empty_weight,
            'cargo_weight': cargo_weight,
            'total_weight': total_weight,
            'profile': profile
        }
        
        self.base_weight = total_weight
        self.target_weight = total_weight
        self.simulation_active = True
        self.stability_counter = 0
        
        # Initialize environmental factors
        self._update_environmental_factors()
        
        print(f"\u2699\ufe0f Weight simulation started for {vehicle_id}")
        print(f"   Vehicle Type: {vehicle_type.value}")
        print(f"   Empty Weight: {empty_weight:.1f} kg")
        print(f"   Cargo Weight: {cargo_weight:.1f} kg")
        print(f"   Total Weight: {total_weight:.1f} kg")
        
        return self.current_vehicle
    
    def stop_simulation(self):
        """Stop the current simulation"""
        self.simulation_active = False
        self.current_vehicle = None
        self.measurement_history.clear()
        print("\u2699\ufe0f Weight simulation stopped")
    
    def get_weight_reading(self) -> SimulatedWeight:
        """Get a simulated weight reading"""
        
        if not self.simulation_active or not self.current_vehicle:
            # Return zero weight if no simulation active
            return SimulatedWeight(
                gross_weight=0.0,
                is_stable=True,
                noise_level=0.0,
                timestamp=datetime.now(),
                measurement_type="gross"
            )
        
        profile = self.current_vehicle['profile']
        
        # Simulate weight settling process
        if abs(self.base_weight - self.target_weight) > 1.0:
            # Weight is settling
            settling_rate = 0.1  # How fast weight settles
            self.base_weight += (self.target_weight - self.base_weight) * settling_rate
            is_stable = False
            self.stability_counter = 0
        else:
            # Weight is close to target, check stability
            self.stability_counter += 1
            is_stable = self.stability_counter > 5 and random.random() < profile.stability_factor
        
        # Add various noise sources
        noise_sources = [
            self._get_electronic_noise(),
            self._get_mechanical_vibration(),
            self._get_wind_effect(),
            self._get_temperature_drift()
        ]
        
        total_noise = sum(noise_sources)
        current_weight = self.base_weight + total_noise
        
        # Ensure weight is non-negative
        current_weight = max(0.0, current_weight)
        
        # Calculate noise level
        noise_level = abs(total_noise) / max(self.base_weight, 1.0)
        
        # Create measurement
        measurement = SimulatedWeight(
            gross_weight=current_weight,
            is_stable=is_stable,
            noise_level=noise_level,
            timestamp=datetime.now(),
            vehicle_id=self.current_vehicle['id'],
            measurement_type="gross"
        )
        
        # Store in history
        self.measurement_history.append(measurement)
        
        # Keep only recent measurements
        if len(self.measurement_history) > 100:
            self.measurement_history.pop(0)
        
        return measurement
    
    def simulate_vehicle_movement(self, movement_type: str = "settling"):
        """Simulate vehicle movement effects on weight"""
        
        if not self.simulation_active:
            return
        
        if movement_type == "settling":
            # Vehicle is settling on scale
            self.target_weight = self.current_vehicle['total_weight']
            self.stability_counter = 0
            
        elif movement_type == "leaving":
            # Vehicle is leaving the scale
            self.target_weight = 0.0
            self.stability_counter = 0
            
        elif movement_type == "repositioning":
            # Vehicle is repositioning on scale
            variance = self.current_vehicle['total_weight'] * 0.1 * random.uniform(-1, 1)
            self.target_weight = self.current_vehicle['total_weight'] + variance
            self.stability_counter = 0
    
    def _update_environmental_factors(self):
        """Update environmental factors that affect weight readings"""
        
        # Wind effect (sinusoidal with random component)
        self.wind_factor = math.sin(time.time() * 0.5) * 2.0 + random.uniform(-1, 1)
        
        # Vibration (higher frequency)
        self.vibration_factor = math.sin(time.time() * 5.0) * 0.5
        
        # Temperature drift (very slow change)
        self.temperature_drift += random.uniform(-0.1, 0.1)
        self.temperature_drift = max(-5.0, min(5.0, self.temperature_drift))  # Limit drift
    
    def _get_electronic_noise(self) -> float:
        """Simulate electronic noise in weight readings"""
        return random.gauss(0, 0.5)  # Gaussian noise with std dev of 0.5 kg
    
    def _get_mechanical_vibration(self) -> float:
        """Simulate mechanical vibration effects"""
        if not self.current_vehicle:
            return 0.0
        
        base_vibration = self.vibration_factor * 1.5
        weight_factor = self.current_vehicle['total_weight'] / 50000  # Heavier vehicles vibrate more
        return base_vibration * (1 + weight_factor)
    
    def _get_wind_effect(self) -> float:
        """Simulate wind effects on weight readings"""
        if not self.current_vehicle:
            return 0.0
        
        # Wind affects larger vehicles more
        wind_sensitivity = {
            VehicleType.TRAILER: 1.5,
            VehicleType.HEAVY_TRUCK: 1.2,
            VehicleType.BUS: 1.1,
            VehicleType.LIGHT_TRUCK: 0.8,
            VehicleType.PICKUP: 0.6,
            VehicleType.VAN: 0.7
        }
        
        sensitivity = wind_sensitivity.get(self.current_vehicle['type'], 1.0)
        return self.wind_factor * sensitivity
    
    def _get_temperature_drift(self) -> float:
        """Simulate temperature-related drift"""
        return self.temperature_drift
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """Get current simulation status"""
        
        status = {
            'active': self.simulation_active,
            'vehicle': self.current_vehicle,
            'environmental_factors': {
                'wind_factor': self.wind_factor,
                'vibration_factor': self.vibration_factor,
                'temperature_drift': self.temperature_drift
            },
            'measurement_count': len(self.measurement_history)
        }
        
        if self.measurement_history:
            latest = self.measurement_history[-1]
            status['latest_reading'] = {
                'weight': latest.gross_weight,
                'stable': latest.is_stable,
                'noise_level': latest.noise_level,
                'timestamp': latest.timestamp.isoformat()
            }
        
        return status
    
    def generate_test_scenario(self, scenario: str) -> Dict[str, Any]:
        """Generate predefined test scenarios"""
        
        scenarios = {
            'light_delivery': {
                'vehicle_type': VehicleType.LIGHT_TRUCK,
                'cargo_percentage': 0.4,
                'description': 'Light delivery truck with partial load'
            },
            'heavy_freight': {
                'vehicle_type': VehicleType.HEAVY_TRUCK,
                'cargo_percentage': 0.9,
                'description': 'Heavy freight truck near capacity'
            },
            'empty_trailer': {
                'vehicle_type': VehicleType.TRAILER,
                'cargo_percentage': 0.0,
                'description': 'Empty trailer returning'
            },
            'overloaded_truck': {
                'vehicle_type': VehicleType.HEAVY_TRUCK,
                'cargo_percentage': 1.2,  # 20% overloaded
                'description': 'Overloaded truck (compliance issue)'
            },
            'unstable_load': {
                'vehicle_type': VehicleType.TRAILER,
                'cargo_percentage': 0.8,
                'description': 'Trailer with unstable load (stability issues)'
            }
        }
        
        if scenario not in scenarios:
            raise ValueError(f"Unknown scenario: {scenario}. Available: {list(scenarios.keys())}")
        
        scenario_config = scenarios[scenario]
        
        # Special handling for unstable load
        if scenario == 'unstable_load':
            vehicle = self.start_simulation(
                vehicle_type=scenario_config['vehicle_type'],
                vehicle_id=f"TEST-{scenario.upper()}",
                cargo_percentage=scenario_config['cargo_percentage']
            )
            # Reduce stability factor for unstable load
            self.current_vehicle['profile'].stability_factor = 0.6
        else:
            vehicle = self.start_simulation(
                vehicle_type=scenario_config['vehicle_type'],
                vehicle_id=f"TEST-{scenario.upper()}",
                cargo_percentage=scenario_config['cargo_percentage']
            )
        
        return {
            'scenario': scenario,
            'description': scenario_config['description'],
            'vehicle': vehicle,
            'config': scenario_config
        }

# Global simulator instance
_weight_simulator = None

def get_weight_simulator() -> WeightSimulator:
    """Get the global weight simulator instance"""
    global _weight_simulator
    if _weight_simulator is None:
        _weight_simulator = WeightSimulator()
    return _weight_simulator

# Convenience functions for easy use
def start_weight_simulation(vehicle_type: str = "heavy_truck", vehicle_id: str = None) -> Dict[str, Any]:
    """Start weight simulation with string vehicle type"""
    simulator = get_weight_simulator()
    vtype = VehicleType(vehicle_type)
    return simulator.start_simulation(vtype, vehicle_id)

def get_simulated_weight() -> Dict[str, Any]:
    """Get current simulated weight reading"""
    simulator = get_weight_simulator()
    reading = simulator.get_weight_reading()
    
    return {
        'weight': reading.gross_weight,
        'stable': reading.is_stable,
        'noise_level': reading.noise_level,
        'timestamp': reading.timestamp.isoformat(),
        'vehicle_id': reading.vehicle_id
    }

def stop_weight_simulation():
    """Stop current weight simulation"""
    simulator = get_weight_simulator()
    simulator.stop_simulation()

if __name__ == "__main__":
    # Demo the weight simulator
    print("Weight Simulator Demo")
    print("="*50)
    
    simulator = WeightSimulator()
    
    # Test different scenarios
    scenarios = ['light_delivery', 'heavy_freight', 'empty_trailer']
    
    for scenario in scenarios:
        print(f"\nTesting scenario: {scenario}")
        config = simulator.generate_test_scenario(scenario)
        print(f"Description: {config['description']}")
        
        # Take several readings
        print("Weight readings:")
        for i in range(10):
            reading = simulator.get_weight_reading()
            stability = "STABLE" if reading.is_stable else "UNSTABLE"
            print(f"  Reading {i+1}: {reading.gross_weight:.1f} kg ({stability})")
            time.sleep(0.1)
        
        simulator.stop_simulation()
        time.sleep(0.5)
