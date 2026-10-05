"""
Компоненти дрона: Battery, Motors, Sensors, Structure
Кожен компонент має собственный reset() метод
"""

import numpy as np
from typing import List, Dict


# ===== БАТАРЕЯ =====

class Battery:
    """
    Батарея дрона
    Сповільнює роботу при розрядженні та деградує з часом
    """
    
    def __init__(self, capacity: float = 100.0):
        """
        Args:
            capacity: Ємність батареї (%)
        """
        
        # Базові параметри
        self.capacity = capacity
        self.max_capacity = capacity
        
        # Поточний стан
        self.charge = capacity  # % заряду (0-100)
        self.temperature = 25.0  # °C
        self.health = 100.0  # % здоров'я батареї
        
        # Цикли розрядження
        self.charge_cycles = 0
        self.deep_discharge_count = 0
        
        # Історія
        self.charge_history = [self.charge]
        self.temperature_history = [self.temperature]
        self.health_history = [self.health]
    
    def discharge(self, amount: float):
        """Розрядити батарею"""
        self.charge = max(0, self.charge - amount)
        
        # Історія
        self.charge_history.append(self.charge)
        
        # Перевірити глибоку розрядку
        if self.charge < 20:
            self.deep_discharge_count += 1
    
    def recharge(self, amount: float):
        """Зарядити батарею"""
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
        """Отримати % заряду"""
        return self.charge
    
    def reset(self):
        """
        RESET батареї на початковий стан
        Використовується коли дрон перезавантажується
        """
        
        # Повернути на 100%
        self.charge = self.max_capacity
        
        # Температура на кімнатну
        self.temperature = 25.0
        
        # Здоров'я трохи менше через деградацію від попередніх циклів
        # але не скидаємо повністю
        cycles_degradation = self.charge_cycles * 0.05  # Менше чим раніше
        self.health = max(50, 100 - cycles_degradation)
        
        # Історія очищується
        self.charge_history = [self.charge]
        self.temperature_history = [self.temperature]
        self.health_history = [self.health]
        
        print("   🔋 Батарея перезавантажена (100%)")


# ===== МОТОРИ =====

class Motors:
    """
    Мотори дрона (4 штуки)
    """
    
    def __init__(self, num_motors: int = 4):
        """
        Args:
            num_motors: Кількість моторів
        """
        
        self.num_motors = num_motors
        
        # Ініціалізувати мотори
        self.motors = []
        for i in range(num_motors):
            motor = {
                'id': i,
                'efficiency': 100.0,      # % ефективності
                'temperature': 25.0,      # °C
                'wear': 0.0,              # % зносу
                'rpm': 0,                 # Обороти
                'status': True            # Працює?
            }
            self.motors.append(motor)
        
        # Історія
        self.efficiency_history = [100.0] * num_motors
        self.temperature_history = [25.0] * num_motors
    
    def apply_stress(self, motor_index: int, stress: float):
        """
        Apply load to a motor and update RPM, temperature, wear,
        and efficiency.
        """

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
        """
        Чи мотор здоровий?
        
        Args:
            motor_id: ID мотора (якщо None - перевіряємо всі)
        """
        
        if motor_id is not None:
            if motor_id >= self.num_motors:
                return False
            motor = self.motors[motor_id]
            return motor['status'] and motor['efficiency'] > 50
        
        # Перевіряємо всі мотори
        return all(self.is_healthy(i) for i in range(self.num_motors))
    
    def reset(self):
        """
        RESET моторів на початковий стан
        """
        
        for i, motor in enumerate(self.motors):
            motor['efficiency'] = 100.0
            motor['temperature'] = 25.0
            motor['wear'] = 0.0  # Повністю очищуємо зносу
            motor['rpm'] = 0
            motor['status'] = True
        
        # Історія очищується
        self.efficiency_history = [100.0] * self.num_motors
        self.temperature_history = [25.0] * self.num_motors
        
        print(f"   ⚙️  {self.num_motors} моторів перезавантажено")


# ===== ДАТЧИКИ =====

class Sensors:
    """
    Датчики дрона (3 штуки: камера, лідар, ультразвук)
    """
    
    def __init__(self, num_sensors: int = 3):
        """
        Args:
            num_sensors: Кількість датчиків
        """
        
        self.num_sensors = num_sensors
        
        # Типи датчиків
        sensor_types = ['camera', 'lidar', 'ultrasonic']
        
        # Ініціалізувати датчики
        self.sensors = []
        for i in range(min(num_sensors, len(sensor_types))):
            sensor = {
                'type': sensor_types[i],
                'accuracy': 90.0,        # % точності
                'dirt_level': 0.0,       # % забруднення (0-100)
                'status': True,          # Працює?
                'calibration_drift': 0.0 # Дрейф калібрування
            }
            self.sensors.append(sensor)
        
        # Історія
        self.accuracy_history = [90.0] * num_sensors
        self.dirt_history = [0.0] * num_sensors
    
    def apply_dirt(self, sensor_id: int, amount: float):
        """
        Забруднити датчик
        
        Args:
            sensor_id: ID датчика (0-2)
            amount: Кількість забруднення
        """
        
        if sensor_id >= len(self.sensors):
            return
        
        sensor = self.sensors[sensor_id]
        sensor['dirt_level'] = min(100, sensor['dirt_level'] + amount)
        
        # Забруднення знижує точність
        sensor['accuracy'] = max(0, 90 - sensor['dirt_level'] * 0.5)
    
    def clean_sensor(self, sensor_id: int):
        """Очистити датчик"""
        
        if sensor_id >= len(self.sensors):
            return
        
        sensor = self.sensors[sensor_id]
        sensor['dirt_level'] = 0.0
        sensor['accuracy'] = 90.0
    
    def apply_calibration_drift(self, sensor_id: int, drift: float):
        """Застосувати дрейф калібрування"""
        
        if sensor_id >= len(self.sensors):
            return
        
        sensor = self.sensors[sensor_id]
        sensor['calibration_drift'] += drift
        
        # Дрейф знижує точність
        sensor['accuracy'] = max(0, 90 - abs(sensor['calibration_drift']))
    
    def get_average_accuracy(self) -> float:
        """Середня точність всіх датчиків"""
        return np.mean([s['accuracy'] for s in self.sensors])
    
    def is_working(self, sensor_id: int = None) -> bool:
        """
        Чи датчик працює?
        
        Args:
            sensor_id: ID датчика (якщо None - перевіряємо всі)
        """
        
        if sensor_id is not None:
            if sensor_id >= len(self.sensors):
                return False
            sensor = self.sensors[sensor_id]
            return sensor['status'] and sensor['accuracy'] > 20
        
        # Перевіряємо всі датчики
        return all(self.is_working(i) for i in range(len(self.sensors)))
    
    def reset(self):
        """
        RESET датчиків на початковий стан
        """
        
        for sensor in self.sensors:
            sensor['accuracy'] = 90.0
            sensor['dirt_level'] = 0.0
            sensor['status'] = True
            sensor['calibration_drift'] = 0.0
        
        # Історія очищується
        self.accuracy_history = [90.0] * len(self.sensors)
        self.dirt_history = [0.0] * len(self.sensors)
        
        print(f"   📡 {len(self.sensors)} датчиків перезавантажено")


# ===== СТРУКТУРА =====

class Structure:
    """
    Структурна цілісність дрона
    Включає пропелери, раму, крила
    """
    
    def __init__(self, num_propellers: int = 4):
        """
        Args:
            num_propellers: Кількість пропелерів
        """
        
        self.num_propellers = num_propellers
        
        # Пропелери
        self.propeller_health = [100.0] * num_propellers  # % здоров'я кожного
        
        # Рама
        self.integrity = 100.0  # % цілісності рами (0-100)
        
        # Статистика
        self.crash_count = 0      # Кількість зіткнень
        self.total_damage = 0.0   # Сумарне пошкодження
        
        # Історія
        self.integrity_history = [100.0]
        self.crash_history = []
    
    def apply_damage(self, damage: float):
        """
        Застосувати пошкодження до структури
        
        Args:
            damage: Сила пошкодження (0-1)
        """
        
        # Розподілити пошкодження
        propeller_damage = damage * 25
        frame_damage = damage * 75
        
        # Пошкодити пропелери
        for i in range(self.num_propellers):
            self.propeller_health[i] = max(0, self.propeller_health[i] - propeller_damage)
        
        # Пошкодити раму
        self.integrity = max(0, self.integrity - frame_damage)
        
        # Записати в історію
        self.total_damage += damage
        self.integrity_history.append(self.integrity)
    
    def record_crash(self, terrain_type: str, damage: float):
        """
        Записати зіткнення
        
        Args:
            terrain_type: Тип терену
            damage: Сила пошкодження
        """
        
        crash_event = {
            'count': self.crash_count,
            'terrain': terrain_type,
            'damage': damage
        }
        self.crash_history.append(crash_event)
        self.crash_count += 1
        
        # Застосувати пошкодження
        self.apply_damage(damage)
    
    def get_structural_integrity(self) -> float:
        """Отримати цілісність структури (0-100%)"""
        return self.integrity
    
    def is_flightworthy(self) -> bool:
        """
        Чи дрон придатний до польоту?
        Потребує:
        - Цілісність > 50%
        - Мінімум 3 пропелера >30%
        """
        
        working_propellers = sum(1 for h in self.propeller_health if h > 30)
        
        return (
            self.integrity > 50 and
            working_propellers >= 3
        )
    
    def reset(self):
        """
        RESET структури на початковий стан
        """
        
        # Пропелери на 100%
        self.propeller_health = [100.0] * self.num_propellers
        
        # Рама на 100%
        self.integrity = 100.0
        
        # Очистити статистику зіткнень
        self.crash_count = 0
        self.total_damage = 0.0
        
        # Історія очищується
        self.integrity_history = [100.0]
        self.crash_history = []
        
        print(f"   🛡️  Структура перезавантажена ({self.num_propellers} пропелерів)")