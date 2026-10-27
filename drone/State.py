import numpy as np


#Battery

class Battery:
    
    def __init__(self, capacity: float = 100.0):
        
        # Basic paramaters
        self.capacity = capacity
        self.max_capacity = capacity
        
        # Current state
        self.charge = capacity  # 
        self.temperature = 25.0  # °C
        self.health = 100.0  #
        
        # Charge cycle
        self.charge_cycles = 0
        self.deep_discharge_count = 0
        
        #history
        self.charge_history = [self.charge]
        self.temperature_history = [self.temperature]
        self.health_history = [self.health]
    
    def discharge(self, amount: float):
        self.charge = max(0, self.charge - amount)
        
        # History
        self.charge_history.append(self.charge)
        
        if self.charge < 20:
            self.deep_discharge_count += 1
    
    def recharge(self, amount: float):
        self.charge = min(self.max_capacity, self.charge + amount)
        self.charge_cycles += 1
        self.charge_history.append(self.charge)
    
    def apply_thermal_stress(self, stress: float):
        """Increase battery temperature because of thermal stress."""

        self.temperature += max(0.0, stress)


    def update_health(self):
        """Reduce battery health when temperature or usage is excessive."""

        if self.temperature > 40:
            overheating = self.temperature - 40
            self.health -= overheating * 0.5

        if self.charge_cycles > 100:
            self.health -= 0.05

        self.health = max(
            0.0,
            min(100.0, self.health),
        )


    def is_healthy(self) -> bool:
        """Return whether the battery is safe to use."""

        return (
            self.health > 20.0
            and self.temperature < 60.0
            and self.charge > 5.0
        )
    
    def get_remaining_range(self) -> float:
        return self.charge
    
    def reset(self):
        
        self.charge = self.max_capacity
        
        self.temperature = 25.0
        
        cycles_degradation = self.charge_cycles * 0.05  # Менше чим раніше
        self.health = max(50, 100 - cycles_degradation)
        
        self.charge_history = [self.charge]
        self.temperature_history = [self.temperature]
        self.health_history = [self.health]


#Motors

class Motors:
    def __init__(self, num_motors: int = 4):
        
        self.num_motors = num_motors
        
        self.motors = []
        for i in range(num_motors):
            motor = {
                'id': i,
                'efficiency': 100.0,    
                'temperature': 25.0,     
                'wear': 0.0,              
                'rpm': 0,                 
                'status': True            
            }
            self.motors.append(motor)
        
        self.efficiency_history = [100.0] * num_motors
        self.temperature_history = [25.0] * num_motors
    
    def apply_stress(self, motor_index: int, stress: float):

        stress = max(0.0, min(1.0, stress))

        motor = self.motors[motor_index]

        motor["rpm"] = 1000.0 + stress * 4500.0

        rpm_factor = max(
            0.0,
            (motor["rpm"] - 4000.0) / 1500.0,
        )

        motor["wear"] += (
            stress * 0.8
            + rpm_factor * 0.6
        )

        motor["temperature"] += (
            stress * 18.0
            + rpm_factor * 12.0
        )

        motor["efficiency"] = max(
            0.0,
            100.0 - motor["wear"],
        )

        if motor["temperature"] > 80:
            motor["status"] = "overheated"
        elif motor["temperature"] > 60:
            motor["status"] = "hot"
        else:
            motor["status"] = "normal"
    
    def update_temperatures(self):
        """Охолодити мотори"""
        for motor in self.motors:
            cooling = (motor['temperature'] - 25) * 0.05
            motor['temperature'] = max(25, motor['temperature'] - cooling)
    
    def get_average_efficiency(self) -> float:
        """Середня ефективність всіх моторів"""
        return np.mean([m['efficiency'] for m in self.motors])
    
    def is_healthy(self, motor_id: int = None) -> bool:
        if motor_id is not None:
            if motor_id >= self.num_motors:
                return False
            motor = self.motors[motor_id]
            return motor['status'] and motor['efficiency'] > 50
        
        # check all motors
        return all(self.is_healthy(i) for i in range(self.num_motors))
    
    def reset(self):
        
        for i, motor in enumerate(self.motors):
            motor['efficiency'] = 100.0
            motor['temperature'] = 25.0
            motor['wear'] = 0.0  # Повністю очищуємо зносу
            motor['rpm'] = 0
            motor['status'] = True
        
        self.efficiency_history = [100.0] * self.num_motors
        self.temperature_history = [25.0] * self.num_motors

# Sensors

class Sensors:
    
    def __init__(self, num_sensors: int = 3):
        
        self.num_sensors = num_sensors
        
        # types of sensors
        sensor_types = ['camera', 'lidar', 'ultrasonic']
        
        self.sensors = []
        for i in range(min(num_sensors, len(sensor_types))):
            sensor = {
                'type': sensor_types[i],
                'accuracy': 90.0,        
                'dirt_level': 0.0,       
                'status': True,          
                'calibration_drift': 0.0
            }
            self.sensors.append(sensor)
        
        self.accuracy_history = [90.0] * num_sensors
        self.dirt_history = [0.0] * num_sensors
    
    def apply_dirt(self, sensor_id: int, amount: float):
        
        if sensor_id >= len(self.sensors):
            return
        
        sensor = self.sensors[sensor_id]
        sensor['dirt_level'] = min(100, sensor['dirt_level'] + amount)
    
        sensor['accuracy'] = max(0, 90 - sensor['dirt_level'] * 0.5)
    
    def clean_sensor(self, sensor_id: int):
        
        if sensor_id >= len(self.sensors):
            return
        
        sensor = self.sensors[sensor_id]
        sensor['dirt_level'] = 0.0
        sensor['accuracy'] = 90.0
    
    def apply_calibration_drift(self, sensor_id: int, drift: float):
        
        if sensor_id >= len(self.sensors):
            return
        
        sensor = self.sensors[sensor_id]
        sensor['calibration_drift'] += drift
        
        sensor['accuracy'] = max(0, 90 - abs(sensor['calibration_drift']))
    
    def get_average_accuracy(self) -> float:
        return np.mean([s['accuracy'] for s in self.sensors])
    
    def is_working(self, sensor_id: int = None) -> bool:
        
        if sensor_id is not None:
            if sensor_id >= len(self.sensors):
                return False
            sensor = self.sensors[sensor_id]
            return sensor['status'] and sensor['accuracy'] > 20
    
        return all(self.is_working(i) for i in range(len(self.sensors)))
    
    def reset(self):
        for sensor in self.sensors:
            sensor['accuracy'] = 90.0
            sensor['dirt_level'] = 0.0
            sensor['status'] = True
            sensor['calibration_drift'] = 0.0
        
        self.accuracy_history = [90.0] * len(self.sensors)
        self.dirt_history = [0.0] * len(self.sensors)

# Structure

class Structure:
    
    def __init__(self, num_propellers: int = 4):
        self.num_propellers = num_propellers
        
        # propellers
        self.propeller_health = [100.0] * num_propellers
        
        # integrity
        self.integrity = 100.0
        
        self.crash_count = 0      
        self.total_damage = 0.0           
        
        self.integrity_history = [100.0]
        self.crash_history = []
    
    def apply_damage(self, damage: float):
        
        # divide damage
        propeller_damage = damage * 25
        frame_damage = damage * 75
        
        # damage propellers
        for i in range(self.num_propellers):
            self.propeller_health[i] = max(0, self.propeller_health[i] - propeller_damage)
        
        # damage integrity
        self.integrity = max(0, self.integrity - frame_damage)
        
        self.total_damage += damage
        self.integrity_history.append(self.integrity)
    
    def record_crash(self, terrain_type: str, damage: float):
        
        crash_event = {
            'count': self.crash_count,
            'terrain': terrain_type,
            'damage': damage
        }
        self.crash_history.append(crash_event)
        self.crash_count += 1
        
        self.apply_damage(damage)
    
    def get_structural_integrity(self) -> float:
        return self.integrity
    
    def is_flightworthy(self) -> bool:
        
        working_propellers = sum(1 for h in self.propeller_health if h > 30)
        
        return (
            self.integrity > 50 and
            working_propellers >= 3
        )
    
    def reset(self):
        
        self.propeller_health = [100.0] * self.num_propellers
        
        self.integrity = 100.0
        
        self.crash_count = 0
        self.total_damage = 0.0
        
        self.integrity_history = [100.0]
        self.crash_history = []