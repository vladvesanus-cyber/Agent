"""
Drone - головний клас дрона
Об'єднує всі компоненти: батарея, мотори, датчики, структура, здоров'я
"""

from typing import Tuple, Dict
from .State import Battery, Motors, Sensors, Structure
from .HealthMonitor import HealthMonitor


class Drone:
    """
    Дрон - об'єднує всі компоненти
    
    Атрибути:
        battery: Батарея дрона
        motors: Мотори (4 штуки)
        sensors: Датчики (камера, лідар, ультразвук)
        structure: Структура (пропелери, рама)
        health_monitor: Моніторинг здоров'я
        position: Позиція дрона (x, y, z)
    """
    
    def __init__(self,
                 battery: Battery,
                 motors: Motors,
                 sensors: Sensors,
                 structure: Structure,
                 health_monitor: HealthMonitor,
                 position: Tuple[float, float, float] = (0, 0, 0)):
        """
        Ініціалізувати дрон з компонентами
        
        Args:
            battery: Батарея
            motors: Мотори (4)
            sensors: Датчики (3)
            structure: Структура
            health_monitor: HealthMonitor
            position: Стартова позиція (x, y, z)
        """
        
        # Компоненти
        self.battery = battery
        self.motors = motors
        self.sensors = sensors
        self.structure = structure
        self.health_monitor = health_monitor
        
        # Позиція та рух
        self.position = list(position)  # [x, y, z]
        self.start_position = list(position)  # Запам'ятати стартову позицію
        
        # Стан польоту
        self.is_flying = False
        self.flight_time = 0
        self.total_distance_traveled = 0
        
        # Історія
        self.position_history = [tuple(self.position)]
        self.collision_history = []
    
    # ===== БАЗОВА ІНФОРМАЦІЯ =====
    
    def get_state(self) -> Dict:
        """
        Отримати повний стан дрона
        
        Returns:
            Словник зі всіма параметрами дрона
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
    
    # ===== ПОЛЬОТ =====
    
    def can_fly(self) -> bool:
        """
        Чи дрон може летіти?
        
        Returns:
            True якщо структура придатна та батарея є
        """
        
        return (
            self.structure.is_flightworthy() and
            self.battery.get_remaining_range() > 5 and
            self.health_monitor.is_system_healthy()
        )
    
    def move(self, dx: float, dy: float, dz: float, target_altitude: float = None) -> bool:
        """
        Переместить дрон
        
        Args:
            dx: Переміщення по X
            dy: Переміщення по Y
            dz: Переміщення по Z (вверх/вниз)
            target_altitude: Цільова висота (опціонально)
        
        Returns:
            True якщо переміщення успішне
        """
        
        if not self.can_fly():
            print("❌ Дрон не може летіти!")
            return False
        
        # ===== РУХАТИСЬ ПО XY =====
        self.position[0] += dx
        self.position[1] += dy
        
        # ===== РУХАТИСЬ ПО Z (висота) =====
        # Якщо передана цільова висота - до неї
        if target_altitude is not None:
            # Поступово мінятись до цільової висоти
            if self.position[2] < target_altitude:
                self.position[2] = min(self.position[2] + 1, target_altitude)
            elif self.position[2] > target_altitude:
                self.position[2] = max(self.position[2] - 1, target_altitude)
        else:
            # Інакше використовувати dz
            self.position[2] = max(0, self.position[2] + dz)
        
        # Обмежити максимальну висоту
        self.position[2] = min(self.position[2], 20)  # Макс 20м
        
        # Записати в історію
        self.position_history.append(tuple(self.position))
        
        # Розрахувати дистанцію
        distance = abs(dx) + abs(dy)
        self.total_distance_traveled += distance
        
        self.flight_time += 1
        
        return True
    
    def take_off(self):
        """Дрон піднімається в повітря"""
        self.is_flying = True
        print("🚁 Дрон піднявся в повітря!")
    
    def land(self):
        """Дрон приземляється"""
        self.is_flying = False
        self.flight_time = 0
        print("✈️  Дрон приземлився!")
    
    # ===== ЕНЕРГІЯ =====
    
    def get_battery_percent(self) -> float:
        """Отримати % батареї"""
        return self.battery.get_remaining_range()
    
    def get_estimated_flight_time(self, energy_per_step: float = 1.0) -> int:
        """
        Розрахувати скільки кроків ще може летіти
        
        Args:
            energy_per_step: Енергія витраченої за крок
        
        Returns:
            Кількість кроків
        """
        
        battery_percent = self.get_battery_percent()
        return int(battery_percent / energy_per_step)
    
    def discharge_battery(self, amount: float):
        """
        Розрядити батарею
        
        Args:
            amount: Відсоток енергії для розрядження (0-100)
        """
        
        self.battery.discharge(amount)
    
    def recharge_battery(self, amount: float):
        """
        Зарядити батарею
        
        Args:
            amount: Відсоток енергії для зарядження (0-100)
        """
        
        self.battery.recharge(amount)
    
    # ===== ЗДОРОВ'Я =====
    
    def get_overall_health(self) -> float:
        """Отримати загальне здоров'я дрона (0-100%)"""
        return self.health_monitor.get_overall_health()
    
    def is_healthy(self) -> bool:
        """Чи дрон здоровий?"""
        return self.health_monitor.is_system_healthy()
    
    def get_critical_problems(self) -> list:
        """Отримати список критичних проблем"""
        return self.health_monitor.get_critical_alerts()
    
    def update_health(self, energy_consumed: float, motor_stress: list,
                     altitude: float, collision_occurred: bool = False,
                     collision_damage: float = 0, ambient_temp: float = 25):
        """
        Оновити здоров'я дрона
        
        Args:
            energy_consumed: % енергії витрачено
            motor_stress: Стрес на кожний мотор [0-1]
            altitude: Висота дрона (м)
            collision_occurred: Чи була колізія?
            collision_damage: Сила пошкодження (0-1)
            ambient_temp: Температура довкілля (°C)
        """
        
        self.health_monitor.update(
            energy_consumed=energy_consumed,
            motor_stress=motor_stress,
            altitude=altitude,
            collision_occurred=collision_occurred,
            collision_damage=collision_damage,
            ambient_temp=ambient_temp
        )
    
    # ===== ДАТЧИКИ =====
    
    def get_sensor_accuracy(self, sensor_index: int = 0) -> float:
        """
        Отримати точність датчика (0-100%)
        
        Args:
            sensor_index: Індекс датчика (0, 1, 2)
        
        Returns:
            Точність датчика
        """
        
        if sensor_index >= len(self.sensors.sensors):
            return 0
        
        sensor = self.sensors.sensors[sensor_index]
        return sensor.get('accuracy', 90)
    
    def get_sensor_status(self) -> Dict:
        """Отримати статус всіх датчиків"""
        
        return {
            'camera': self.sensors.sensors[0]['status'],
            'lidar': self.sensors.sensors[1]['status'],
            'ultrasonic': self.sensors.sensors[2]['status']
        }
    
    # ===== ПОЗИЦІЯ =====
    
    def get_distance_to_home(self) -> float:
        """
        Розрахувати дистанцію до дому
        
        Returns:
            Манхеттенська дистанція
        """
        
        start_x, start_y = self.start_position[0], self.start_position[1]
        curr_x, curr_y = self.position[0], self.position[1]
        
        return abs(curr_x - start_x) + abs(curr_y - start_y)
    
    def is_at_home(self, tolerance: float = 1.0) -> bool:
        """
        Чи дрон вдома?
        
        Args:
            tolerance: Допуск дистанції
        
        Returns:
            True якщо близько до дому
        """
        
        return self.get_distance_to_home() <= tolerance
    
    def get_position(self) -> Tuple[float, float, float]:
        """Отримати поточну позицію"""
        return tuple(self.position)
    
    def get_altitude(self) -> float:
        """Отримати висоту (Z)"""
        return self.position[2]
    
    # ===== КОЛІЗІЯ =====
    
    def record_collision(self, terrain_type: str, damage: float):
        """
        Записати колізію в історію
        
        Args:
            terrain_type: Тип терену (hard_obstacle, tree, water, etc)
            damage: Сила пошкодження (0-1)
        """
        
        collision_event = {
            'position': tuple(self.position),
            'terrain_type': terrain_type,
            'damage': damage,
            'timestamp': len(self.collision_history)
        }
        
        self.collision_history.append(collision_event)
    
    def get_collision_count(self) -> int:
        """Отримати кількість колізій"""
        return len(self.collision_history)
    
    # ===== RESET =====
    
    def reset(self):
        """
        Перезавантажити дрон на стартову позицію
        """
        
        # Позиція
        self.position = list(self.start_position)
        self.position_history = [tuple(self.position)]
        
        # Стан польоту
        self.is_flying = False
        self.flight_time = 0
        self.total_distance_traveled = 0
        
        # Компоненти
        self.battery.reset()
        self.motors.reset()
        self.sensors.reset()
        self.structure.reset()
        self.health_monitor.reset()
        
        # Історія
        self.collision_history = []
        
        print("🔄 Дрон перезавантажено на стартову позицію")
    
    # ===== ДІАГНОСТИКА =====
    
    def diagnose(self) -> str:
        """
        Повна діагностика здоров'я дрона
        
        Returns:
            Рядок з інформацією про стан дрона
        """
        
        critical = self.health_monitor.get_critical_alerts()
        
        if critical:
            alerts_str = ", ".join(critical)
            return f"🚨 КРИТИЧНІ ПРОБЛЕМИ: {alerts_str}"
        
        health = self.get_overall_health()
        
        if health > 80:
            return "✅ Дрон в відмінному стані!"
        elif health > 60:
            return "⚠️  Дрон потребує обслуговування"
        elif health > 40:
            return "⚠️⚠️  Дрон в поганому стані!"
        else:
            return "🚨 ДРОН НЕБЕЗПЕЧНИЙ!"
    
    def print_status(self):
        """Вивести статус дрона красиво"""
        
        print("\n" + "="*50)
        print("🚁 СТАТУС ДРОНА")
        print("="*50)
        
        print(f"\n📍 Позиція: ({self.position[0]:.1f}, {self.position[1]:.1f}, {self.position[2]:.1f}m)")
        print(f"📏 До дому: {self.get_distance_to_home():.1f}")
        print(f"🚀 Здоров'я: {self.get_overall_health():.1f}%")
        print(f"🔋 Батарея: {self.get_battery_percent():.1f}%")
        print(f"💢 Колізій: {self.get_collision_count()}")
        print(f"✈️  На висоті: {'Так' if self.is_flying else 'Ні'}")
        
        print(f"\n{self.diagnose()}")
        print("="*50 + "\n")