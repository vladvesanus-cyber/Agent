class Battery:
    def __init__(self, capacity: float):
        self.capacity = capacity
        self.charge = capacity
        self.full_cycles = 0
        self.temperature = 25.0
        self.health = 100.0
        self.ambient_temp = 25.0
    
    def discharge(self, amount: float):
        """Розраховує енергію за висоту"""
        # Виправлено: discharges → discharge
        self.charge = max(0, self.charge - amount)
    
    def recharge(self):
        self.charge = self.capacity
        self.full_cycles += 1
        self.update_health()
    
    def get_remaining_range(self) -> float:
        """Повертає % залишку батареї"""
        return (self.charge / self.capacity) * 100
    
    def apply_thermal_stress(self, stress: float):
        """Температура зростає з стресом, але охолоджується"""
        self.temperature += stress
        # Охолодження до навколишньої температури
        cooling = (self.temperature - self.ambient_temp) * 0.05
        self.temperature = max(self.ambient_temp, self.temperature - cooling)
    
    def update_health(self):
        """Деградація від циклів та температури"""
        cycle_degradation = min(50, self.full_cycles * 0.5)
        temp_stress = max(0, (self.temperature - 40) * 0.2)
        self.health = max(0, 100 - cycle_degradation - temp_stress)
    
    def is_healthy(self) -> bool:
        return self.health > 20 and self.temperature < 50

class Motors:
    def __init__(self, num_motors: int = 4):
        self.num_motors = num_motors
        self.motors = [
            {
                'status': True,
                'rpm': 0,
                'max_rpm': 8000,
                'vibration': 0,
                'temperature': 25,
                'stress': 0,
                'wear': 0,
                'efficiency': 100
            }
            for _ in range(num_motors)
        ]
    
    def set_rpm(self, motor_index: int, rpm: float):
        if 0 <= motor_index < self.num_motors:
            self.motors[motor_index]['rpm'] = min(rpm, 8000)
    
    def apply_stress(self, motor_index: int):
        """Розрахунок стресу як середнє від трьох факторів"""
        if 0 <= motor_index < self.num_motors:
            motor = self.motors[motor_index]
            rpm_stress = motor['rpm'] / motor['max_rpm']
            temp_stress = max(0, (motor['temperature'] - 25) / 75)
            vib_stress = motor['vibration'] / 10
            
            motor['stress'] = (rpm_stress + temp_stress + vib_stress) / 3
    
    def update_wear(self, motor_index: int):
        """Оновити знос на основі стресу"""
        if 0 <= motor_index < self.num_motors:
            motor = self.motors[motor_index]
            motor['wear'] += motor['stress'] * 0.5
            motor['efficiency'] = max(0, 100 - motor['wear'])
    
    def is_healthy(self, motor_index: int) -> bool:
        if 0 <= motor_index < self.num_motors:
            motor = self.motors[motor_index]
            return (motor['wear'] < 70 and 
                    motor['temperature'] < 80 and 
                    motor['vibration'] < 8 and
                    motor['status'])
        return False

from random import gauss

class Sensors:
    def __init__(self, num_sensors: int = 3):
        self.num_sensors = num_sensors
        self.sensors = [
            {
                'status': True,
                'type': ['gps', 'camera', 'lidar'][i % 3],
                'noise_level': 0.1,
                'calibration': 1.0,
                'reliability': 100,
                'dirt_level': 0,
                'measure_error': 0
            }
            for i in range(num_sensors)
        ]
    
    def measure(self, sensor_index: int, true_value: float) -> float:
        """Виміри з гаусовим шумом"""
        if 0 <= sensor_index < self.num_sensors:
            sensor = self.sensors[sensor_index]
            noise = gauss(0, sensor['noise_level'])
            measured = (true_value + noise) * sensor['calibration']
            sensor['measure_error'] = abs(measured - true_value)
            return measured
    
    def apply_dirt(self, sensor_index: int, dirt_amount: float):
        if 0 <= sensor_index < self.num_sensors:
            self.sensors[sensor_index]['dirt_level'] += dirt_amount
            self.sensors[sensor_index]['reliability'] = max(0, 100 - self.sensors[sensor_index]['dirt_level'])
    
    def get_accuracy(self, sensor_index: int, altitude: float = 0) -> float:
        """Точність датчика залежить від висоти та забруднення"""
        if 0 <= sensor_index < self.num_sensors:
            sensor = self.sensors[sensor_index]
            
            base = sensor['reliability'] / 100
            calibration = sensor['calibration']
            dirt = (100 - sensor['dirt_level']) / 100
            altitude_factor = max(0, 1 - (altitude ** 1.5) * 0.02)
            
            accuracy = base * calibration * dirt * altitude_factor * 100
            return min(100, max(0, accuracy))
        return 0
    
    def calibrate(self, sensor_index: int):
        if 0 <= sensor_index < self.num_sensors:
            self.sensors[sensor_index]['calibration'] = 1.0

class Structure:
    def __init__(self, num_propellers: int = 4):
        self.integrity = 100.0
        self.num_propellers = num_propellers
        self.propeller_health = [100.0] * num_propellers  # ← Змінено на здоров'я
        self.antenna_status = True
        self.crash_count = 0
        self.impact_log = []
    
    def apply_damage(self, severity: float, location: str = "unknown"):
        """Застосувати пошкодження"""
        self.integrity = max(0, self.integrity - severity)
        self.crash_count += 1
        self.impact_log.append({'location': location, 'severity': severity})
    
    def damage_propeller(self, propeller_index: int, damage: float):
        if 0 <= propeller_index < self.num_propellers:
            self.propeller_health[propeller_index] = max(0, self.propeller_health[propeller_index] - damage)
    
    def get_structural_integrity(self) -> float:
        """Загальна цілісність 0-100"""
        avg_propeller = sum(self.propeller_health) / self.num_propellers
        # 50% рама, 50% пропелери
        return (self.integrity * 0.5 + avg_propeller * 0.5)
    
    def is_flightworthy(self) -> bool:
        """Чи дрон може летіти?"""
        working_propellers = sum(1 for h in self.propeller_health if h > 30)
        return (self.integrity > 50 and 
                working_propellers >= 2 and 
                self.antenna_status)
    
    def aerodynamic_efficiency(self) -> float:
        """0-1, де 1 = ідеально"""
        integrity_factor = self.integrity / 100
        propeller_factor = sum(self.propeller_health) / (self.num_propellers * 100)
        return integrity_factor * propeller_factor