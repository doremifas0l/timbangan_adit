# Weight validator - validates weight readings and stability
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from statistics import stdev, mean

@dataclass
class WeightReading:
    """Represents a single weight reading"""
    weight: float
    timestamp: datetime
    is_stable: bool
    raw_data: str = ""

class WeightValidator:
    """Validates weight readings for accuracy and stability"""
    
    def __init__(self):
        # Default validation settings
        self.min_weight = 0.0          # Minimum valid weight
        self.max_weight = 100000.0     # Maximum valid weight (100 tons)
        self.stability_threshold = 5.0  # Maximum deviation for stability (kg)
        self.stability_duration = 3.0   # Seconds weight must be stable
        self.reading_history: List[WeightReading] = []
        self.max_history = 20          # Maximum readings to keep in history
        
    def configure(
        self, 
        min_weight: float = None,
        max_weight: float = None, 
        stability_threshold: float = None,
        stability_duration: float = None
    ):
        """Configure validation parameters"""
        if min_weight is not None:
            self.min_weight = min_weight
        if max_weight is not None:
            self.max_weight = max_weight
        if stability_threshold is not None:
            self.stability_threshold = stability_threshold
        if stability_duration is not None:
            self.stability_duration = stability_duration
    
    def validate_weight(self, weight: float) -> Dict[str, Any]:
        """Validate a single weight reading"""
        validation_result = {
            'is_valid': True,
            'weight': weight,
            'errors': [],
            'warnings': []
        }
        
        # Basic range validation
        if weight < self.min_weight:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Weight {weight} kg is below minimum ({self.min_weight} kg)")
            
        if weight > self.max_weight:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Weight {weight} kg exceeds maximum ({self.max_weight} kg)")
            
        # Check for reasonable weight (not exactly zero unless expected)
        if weight == 0.0:
            validation_result['warnings'].append("Zero weight reading detected")
            
        # Check for suspicious round numbers (might indicate manual entry or error)
        if weight % 10 == 0 and weight > 100:
            validation_result['warnings'].append("Suspicious round number detected")
            
        return validation_result
    
    def add_reading(self, weight: float, is_stable: bool = None, raw_data: str = "") -> WeightReading:
        """Add a weight reading to history"""
        
        # Auto-detect stability if not provided
        if is_stable is None:
            is_stable = self.is_weight_stable(weight)
            
        reading = WeightReading(
            weight=weight,
            timestamp=datetime.utcnow(),
            is_stable=is_stable,
            raw_data=raw_data
        )
        
        self.reading_history.append(reading)
        
        # Maintain history size
        if len(self.reading_history) > self.max_history:
            self.reading_history = self.reading_history[-self.max_history:]
            
        return reading
    
    def is_weight_stable(self, current_weight: float = None) -> bool:
        """Determine if weight is stable based on recent readings"""
        
        if len(self.reading_history) < 3:
            return False  # Need at least 3 readings for stability analysis
            
        # Get recent readings within stability duration
        now = datetime.utcnow()
        stability_cutoff = now - timedelta(seconds=self.stability_duration)
        
        recent_readings = [
            r for r in self.reading_history[-10:] 
            if r.timestamp >= stability_cutoff
        ]
        
        if len(recent_readings) < 3:
            return False
            
        # Calculate weight variation
        weights = [r.weight for r in recent_readings]
        
        if current_weight is not None:
            weights.append(current_weight)
            
        # Check if all weights are within stability threshold
        avg_weight = mean(weights)
        max_deviation = max(abs(w - avg_weight) for w in weights)
        
        return max_deviation <= self.stability_threshold
    
    def get_stable_weight(self) -> Optional[float]:
        """Get stable weight if available"""
        
        if not self.is_weight_stable():
            return None
            
        # Return average of recent stable readings
        now = datetime.utcnow()
        stability_cutoff = now - timedelta(seconds=self.stability_duration)
        
        recent_readings = [
            r for r in self.reading_history[-10:] 
            if r.timestamp >= stability_cutoff
        ]
        
        if recent_readings:
            weights = [r.weight for r in recent_readings]
            return round(mean(weights), 1)  # Round to 1 decimal place
            
        return None
    
    def get_stability_status(self) -> Dict[str, Any]:
        """Get detailed stability status"""
        
        status = {
            'is_stable': False,
            'stable_weight': None,
            'deviation': None,
            'reading_count': len(self.reading_history),
            'stability_duration': 0.0,
            'message': ""
        }
        
        if len(self.reading_history) < 3:
            status['message'] = "Insufficient readings for stability analysis"
            return status
            
        # Check current stability
        now = datetime.utcnow()
        stability_cutoff = now - timedelta(seconds=self.stability_duration)
        
        recent_readings = [
            r for r in self.reading_history[-10:] 
            if r.timestamp >= stability_cutoff
        ]
        
        if len(recent_readings) < 3:
            status['message'] = "Waiting for stable readings"
            return status
            
        # Calculate statistics
        weights = [r.weight for r in recent_readings]
        avg_weight = mean(weights)
        max_deviation = max(abs(w - avg_weight) for w in weights)
        
        status['deviation'] = max_deviation
        
        if max_deviation <= self.stability_threshold:
            status['is_stable'] = True
            status['stable_weight'] = round(avg_weight, 1)
            status['stability_duration'] = (now - recent_readings[0].timestamp).total_seconds()
            status['message'] = f"Weight stable at {status['stable_weight']} kg"
        else:
            status['message'] = f"Weight fluctuating (±{max_deviation:.1f} kg)"
            
        return status
    
    def detect_weight_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalies in weight readings"""
        
        anomalies = []
        
        if len(self.reading_history) < 5:
            return anomalies
            
        weights = [r.weight for r in self.reading_history]
        
        # Detect sudden jumps
        for i in range(1, len(weights)):
            diff = abs(weights[i] - weights[i-1])
            
            # If weight changes by more than 1000kg between readings, it's suspicious
            if diff > 1000:
                anomalies.append({
                    'type': 'sudden_jump',
                    'description': f'Weight jumped by {diff:.1f} kg',
                    'reading_index': i,
                    'weight': weights[i],
                    'previous_weight': weights[i-1]
                })
                
        # Detect oscillating weights
        if len(weights) >= 5:
            # Check for alternating high/low pattern
            last_5 = weights[-5:]
            differences = [last_5[i+1] - last_5[i] for i in range(len(last_5)-1)]
            
            # If differences alternate in sign and are significant
            if len(differences) >= 4:
                signs = [1 if d > 0 else -1 for d in differences]
                if all(signs[i] != signs[i+1] for i in range(len(signs)-1)):
                    if all(abs(d) > 50 for d in differences):  # 50kg threshold
                        anomalies.append({
                            'type': 'oscillation',
                            'description': 'Weight oscillating significantly',
                            'amplitude': max(abs(d) for d in differences)
                        })
                        
        return anomalies
    
    def reset(self):
        """Reset validator state"""
        self.reading_history.clear()
    
    def get_reading_statistics(self) -> Dict[str, Any]:
        """Get statistics about recent readings"""
        
        if not self.reading_history:
            return {}
            
        weights = [r.weight for r in self.reading_history]
        
        stats = {
            'count': len(weights),
            'min': min(weights),
            'max': max(weights),
            'average': round(mean(weights), 1),
            'latest': weights[-1],
            'stable_readings': len([r for r in self.reading_history if r.is_stable])
        }
        
        if len(weights) > 1:
            stats['std_dev'] = round(stdev(weights), 2)
            stats['range'] = stats['max'] - stats['min']
            
        return stats
    
    def export_readings(self, format: str = 'csv') -> str:
        """Export reading history in specified format"""
        
        if format.lower() == 'csv':
            lines = ['timestamp,weight,is_stable,raw_data']
            
            for reading in self.reading_history:
                lines.append(f"{reading.timestamp.isoformat()},{reading.weight},{reading.is_stable},{reading.raw_data}")
                
            return '\n'.join(lines)
            
        elif format.lower() == 'json':
            import json
            data = [
                {
                    'timestamp': r.timestamp.isoformat(),
                    'weight': r.weight,
                    'is_stable': r.is_stable,
                    'raw_data': r.raw_data
                }
                for r in self.reading_history
            ]
            return json.dumps(data, indent=2)
            
        else:
            raise ValueError(f"Unsupported export format: {format}")
