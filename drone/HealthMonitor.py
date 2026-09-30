import numpy as np

class HealthMonitor:
    """
    Моніторинг здоров'я дрона
    Оновлює температуру та забруднення
    """
    
    def __init__(self, battery, motors, sensors, structure):
        self.battery = battery
        self.motors = motors
        self.sensors = sensors
        self.structure = structure
        
        self.health_history = []
        self.temperature_history = []
    
    def update(self, 
               energy_consumed: float,      # % енергії витраченої за крок
               motor_stress: list,          # Стрес кожного мотора [0-1]
               altitude: float,             # Висота дрона
               collision_occurred: bool,    # Чи був удар?
               collision_severity: float,   # Сила удару (0-1)
               ambient_temp: float = 25):   # Температура довкілля
        """
        Оновити здоров'я дрона за один крок
        
        Args:
            energy_consumed: Скільки % батареї витрачено
            motor_stress: Список стресів для кожного мотора
            altitude: Висота дрона
            collision_occurred: Чи дрон зіткнувся?
            collision_severity: Сила зіткнення
            ambient_temp: Температура довкілля (дефолт 25°C)
        """
        
        # ===== ОНОВИТИ ТЕМПЕРАТУРУ БАТАРЕЇ =====
        self._update_battery_temperature(energy_consumed, ambient_temp)
        
        # ===== ОНОВИТИ ТЕМПЕРАТУРУ МОТОРІВ =====
        self._update_motor_temperatures(motor_stress, altitude, ambient_temp)
        
        # ===== ОНОВИТИ ЗАБРУДНЕННЯ ДАТЧИКІВ =====
        self._update_sensor_contamination(altitude, collision_occurred, collision_severity)
        
        # ===== ОНОВИТИ ЗАГАЛЬНЕ ЗДОРОВ'Я =====
        self._calculate_overall_health()
    
    # ===== БАТАРЕЯ =====
    
    def _update_battery_temperature(self, energy_consumed: float, ambient_temp: float):
        """Температура батареї зростає з розрядженням"""
        
        # Кожен % витраченої енергії = +0.5°C
        heat_from_discharge = energy_consumed * 0.5
        
        # Застосуємо тепло
        self.battery.apply_thermal_stress(heat_from_discharge)
        
        # Охолодження до навколишньої температури
        cooling = (self.battery.temperature - ambient_temp) * 0.05
        self.battery.temperature = max(ambient_temp, self.battery.temperature - cooling)
        
        # Якщо тепло - деградація здоров'я
        if self.battery.temperature > 45:
            thermal_stress = (self.battery.temperature - 45) * 0.1
            self.battery.health -= thermal_stress
    
    # ===== МОТОРИ =====
    
    def _update_motor_temperatures(self, motor_stress: list, altitude: float, ambient_temp: float):
        """Температура моторів зростає зі стресом"""
        
        for i, stress in enumerate(motor_stress):
            motor = self.motors.motors[i]
            
            # Базова температура від стресу: 25°C + стрес * 50
            # При стресі 1.0 (максимум) → температура 75°C
            motor_heat = stress * 50
            motor['temperature'] = ambient_temp + motor_heat
            
            # Висока висота = важче охолоджується (тонше повітря)
            altitude_factor = 1 + (altitude / 20) * 0.3  # +30% при висоті 20м
            
            # Охолодження (повільніше на висоті)
            cooling = (motor['temperature'] - ambient_temp) * 0.03 / altitude_factor
            motor['temperature'] = max(ambient_temp, motor['temperature'] - cooling)
            
            # Оновити стрес та знос
            self.motors.apply_stress(i)
            self.motors.update_wear(i)
            
            # Якщо мотор перегрівається - деградація
            if motor['temperature'] > 80:
                overheat_stress = (motor['temperature'] - 80) * 0.1
                motor['wear'] += overheat_stress
                motor['efficiency'] = max(0, 100 - motor['wear'])
    
    # ===== ДАТЧИКИ =====
    
    def _update_sensor_contamination(self, altitude: float, 
                                    collision_occurred: bool, 
                                    collision_severity: float):
        """Забруднення датчиків від пилу та ударів"""
        
        for i, sensor in enumerate(self.sensors.sensors):
            # ===== Забруднення від висоти (пил) =====
            # На низькій висоті більше пилу
            if altitude <= 5:
                dust_factor = (5 - altitude) * 0.2  # 0-1 залежно від висоти
                sensor['dirt_level'] += dust_factor * 0.1  # +0.1% за крок
            
            # ===== Забруднення від зіткнення =====
            if collision_occurred:
                # Передня камера потерпає більше
                if sensor['type'] == 'camera':
                    sensor['dirt_level'] += collision_severity * 20  # +20% за крах
                # Лідар теж потерпає
                elif sensor['type'] == 'lidar':
                    sensor['dirt_level'] += collision_severity * 10  # +10%
            
            # Максимум забруднення = 100%
            sensor['dirt_level'] = min(100, sensor['dirt_level'])
            
            # Оновити надійність
            sensor['reliability'] = max(0, 100 - sensor['dirt_level'])
            
            # Якщо забруднено > 70% - потребує чистки
            if sensor['dirt_level'] > 70:
                # Гіршає калібрування від забруднення
                sensor['calibration'] *= 0.99  # -1% за крок
    
    # ===== ЗАГАЛЬНЕ ЗДОРОВ'Я =====
    
    def _calculate_overall_health(self):
        """Розрахувати загальне здоров'я дрона"""
        
        battery_health = self.battery.health
        
        motor_health = np.mean([
            m['efficiency'] for m in self.motors.motors
        ])
        
        sensor_health = np.mean([
            s['reliability'] for s in self.sensors.sensors
        ])
        
        structure_health = self.structure.get_structural_integrity()
        
        # Загальне здоров'я (вживання)
        overall = (
            battery_health * 0.3 +       # 30% від батареї
            motor_health * 0.3 +         # 30% від моторів
            sensor_health * 0.2 +        # 20% від датчиків
            structure_health * 0.2       # 20% від структури
        )
        
        self.health_history.append(overall)
    
    def get_overall_health(self) -> float:
        """Повернути поточне загальне здоров'я (0-100)"""
        return self.health_history[-1] if self.health_history else 100.0
    
    def is_system_healthy(self) -> bool:
        """Чи система працює нормально?"""
        return (
            self.battery.is_healthy() and
            all(self.motors.is_healthy(i) for i in range(self.motors.num_motors)) and
            self.structure.is_flightworthy()
        )
    
    def get_critical_alerts(self) -> list:
        """Повернути критичні проблеми"""
        alerts = []
        
        if self.battery.temperature > 50:
            alerts.append("🔥 БАТАРЕЯ ПЕРЕГРІТА!")
        
        if self.battery.health < 30:
            alerts.append("⚠️ Батарея критично деградована")
        
        for i, motor in enumerate(self.motors.motors):
            if motor['temperature'] > 85:
                alerts.append(f"🔥 Мотор {i} перегрівається!")
            if motor['efficiency'] < 50:
                alerts.append(f"⚠️ Мотор {i} дуже зношений")
        
        for i, sensor in enumerate(self.sensors.sensors):
            if sensor['dirt_level'] > 80:
                alerts.append(f"🔭 {sensor['type']} #{i} дуже забруднений")
        
        if not self.structure.is_flightworthy():
            alerts.append("❌ ДРОН НЕ ПРИДАТНИЙ ДО ПОЛЬОТУ!")
        
        return alerts

