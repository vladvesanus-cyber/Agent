from typing import Tuple, Dict
from .State import Battery, Motors, Sensors, Structure
from .HealthMonitor import HealthMonitor


class Drone:
    
    def __init__(self,
                 battery: Battery,
                 motors: Motors,
                 sensors: Sensors,
                 structure: Structure,
                 health_monitor: HealthMonitor,
                 position: Tuple[float, float, float] = (0, 0, 0)):
        # Components
        self.battery = battery
        self.motors = motors
        self.sensors = sensors
        self.structure = structure
        self.health_monitor = health_monitor
        
        # Position
        self.position = list(position)  # [x, y, z]
        self.start_position = list(position)  # remember start position
        
        # state of fly
        self.is_flying = False
        self.flight_time = 0
        self.total_distance_traveled = 0
        
        # history
        self.position_history = [tuple(self.position)]
        self.collision_history = []
    
    # ===== БАЗОВА ІНФОРМАЦІЯ =====
    
    def get_state(self) -> Dict:
        """
        get full state of drone
        
        Returns:
            Dictionary with all paramaters
        """
        
        return {
            'position': tuple(self.position),
            'is_flying': self.is_flying,
            'flight_time': self.flight_time,
            'total_distance': self.total_distance_traveled,
            
            'battery': {
                'charge_percent': self.battery.get_remaining_range(),
                'temperature': self.battery.temperature,
                'health': self.battery.health,
                'is_healthy': self.battery.is_healthy(),
                'cycles': self.battery.charge_cycles
            },
            
            'motors': [
                {
                    'efficiency': m['efficiency'],
                    'temperature': m['temperature'],
                    'wear': m['wear'],
                    'status': 'OK' if m['efficiency'] > 50 else 'DEGRADED'
                }
                for m in self.motors.motors
            ],
            
            'sensors': [
                {
                    'type': s['type'],
                    'accuracy': s.get('accuracy', 90),
                    'dirt_level': s['dirt_level'],
                    'status': 'OK' if s['status'] else 'FAILED'
                }
                for s in self.sensors.sensors
            ],
            
            'structure': {
                'integrity': self.structure.get_structural_integrity(),
                'is_flightworthy': self.structure.is_flightworthy(),
                'crash_count': self.structure.crash_count,
                'propeller_health': self.structure.propeller_health
            },
            
            'health': {
                'overall': self.health_monitor.get_overall_health(),
                'is_healthy': self.health_monitor.is_system_healthy(),
                'critical_alerts': self.health_monitor.get_critical_alerts()
            }
        }
    
    # Fly
    
    def can_fly(self) -> bool:
        
        return (
            self.structure.is_flightworthy() and
            self.battery.get_remaining_range() > 5 and
            self.health_monitor.is_system_healthy()
        )
    
    def move(self, dx: float, dy: float, dz: float, target_altitude: float = None) -> bool:
        
        if not self.can_fly():
            return False
        
        # move on xy
        self.position[0] += dx
        self.position[1] += dy
        
        # move on z
        # if have target altitude, change altitude to it
        if target_altitude is not None:
            # Gradually adjust to the target altitude
            if self.position[2] < target_altitude:
                self.position[2] = min(self.position[2] + 1, target_altitude)
            elif self.position[2] > target_altitude:
                self.position[2] = max(self.position[2] - 1, target_altitude)
        else:
            # otherwise use dz
            self.position[2] = max(0, self.position[2] + dz)
        
        # limit max height
        self.position[2] = min(self.position[2], 20)  # Макс 20м
        
        # write in history
        self.position_history.append(tuple(self.position))
        
        # calculate distance
        distance = abs(dx) + abs(dy)
        self.total_distance_traveled += distance
        
        self.flight_time += 1
        
        return True
    
    def take_off(self):
        """Drone is in air"""
        self.is_flying = True
    
    def land(self):
        """Drone land"""
        self.is_flying = False
        self.flight_time = 0
    
    # Energy
    
    def get_battery_percent(self) -> float:
        """get battery percent"""
        return self.battery.get_remaining_range()
    
    def get_estimated_flight_time(self, energy_per_step: float = 1.0) -> int:
        """
        how long can fly
        """
        
        battery_percent = self.get_battery_percent()
        return int(battery_percent / energy_per_step)
    
    def discharge_battery(self, amount: float):
        
        self.battery.discharge(amount)
    
    def recharge_battery(self, amount: float):
        
        self.battery.recharge(amount)
    
    # Health
    
    def get_overall_health(self) -> float:
        return self.health_monitor.get_overall_health()
    
    def is_healthy(self) -> bool:
        return self.health_monitor.is_system_healthy()
    
    def get_critical_problems(self) -> list:
        return self.health_monitor.get_critical_alerts()
    
    def update_health(self, energy_consumed: float, motor_stress: list,
                     altitude: float, collision_occurred: bool = False,
                     collision_damage: float = 0, ambient_temp: float = 25):
        
        self.health_monitor.update(
            energy_consumed=energy_consumed,
            motor_stress=motor_stress,
            altitude=altitude,
            collision_occurred=collision_occurred,
            collision_damage=collision_damage,
            ambient_temp=ambient_temp
        )
    
    #Sensors
    
    def get_sensor_accuracy(self, sensor_index: int = 0) -> float:
        
        if sensor_index >= len(self.sensors.sensors):
            return 0
        
        sensor = self.sensors.sensors[sensor_index]
        return sensor.get('accuracy', 90)
    
    def get_sensor_status(self) -> Dict:
        
        return {
            'camera': self.sensors.sensors[0]['status'],
            'lidar': self.sensors.sensors[1]['status'],
            'ultrasonic': self.sensors.sensors[2]['status']
        }
    
    #position
    
    def get_distance_to_home(self) -> float:
        
        start_x, start_y = self.start_position[0], self.start_position[1]
        curr_x, curr_y = self.position[0], self.position[1]
        
        return abs(curr_x - start_x) + abs(curr_y - start_y)
    
    def is_at_home(self, tolerance: float = 1.0) -> bool:
        return self.get_distance_to_home() <= tolerance
    
    def get_position(self) -> Tuple[float, float, float]:
        return tuple(self.position)
    
    def get_altitude(self) -> float:
        return self.position[2]
    
    # Colition
    
    def record_collision(self, terrain_type: str, damage: float):
        
        collision_event = {
            'position': tuple(self.position),
            'terrain_type': terrain_type,
            'damage': damage,
            'timestamp': len(self.collision_history)
        }
        
        self.collision_history.append(collision_event)
    
    def get_collision_count(self) -> int:
        return len(self.collision_history)
    
    # ===== RESET =====
    
    def reset(self):
        
        # Position
        self.position = list(self.start_position)
        self.position_history = [tuple(self.position)]
        
        # State of fly
        self.is_flying = False
        self.flight_time = 0
        self.total_distance_traveled = 0
        
        # Components
        self.battery.reset()
        self.motors.reset()
        self.sensors.reset()
        self.structure.reset()
        self.health_monitor.reset()
        
        # History
        self.collision_history = []