"""
HealthMonitor - моніторинг здоров'я дрона
"""

import numpy as np
from typing import List, Dict


class HealthMonitor:
    """
    Слідкує за здоров'ям дрона
    Оновлює стан на основі параметрів
    """
    
    def __init__(self, battery, motors, sensors, structure):
        self.battery = battery
        self.motors = motors
        self.sensors = sensors
        self.structure = structure
        
        self.health_history = []
        self.last_update = {
            'energy_consumed': 0,
            'motor_stress': [0, 0, 0, 0],
            'altitude': 0,
            'collision_occurred': False,
            'collision_damage': 0,
            'ambient_temp': 25
        }
    
    def update(self,
               energy_consumed: float,
               motor_stress: List[float],
               altitude: float,
               collision_occurred: bool = False,
               collision_damage: float = 0.0,
               ambient_temp: float = 25.0):
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
        
        # Записати останнє оновлення
        self.last_update = {
            'energy_consumed': energy_consumed,
            'motor_stress': motor_stress,
            'altitude': altitude,
            'collision_occurred': collision_occurred,
            'collision_damage': collision_damage,
            'ambient_temp': ambient_temp
        }
        
        # ===== БАТАРЕЯ =====
        self._update_battery(energy_consumed, ambient_temp)
        
        # ===== МОТОРИ =====
        self._update_motors(motor_stress, altitude, ambient_temp)
        
        # ===== ДАТЧИКИ =====
        self._update_sensors(altitude, collision_occurred, collision_damage)
        
        # ===== СТРУКТУРА - ПОШКОДЖЕННЯ ВІД КОЛІЗІЇ =====
        if collision_occurred and collision_damage > 0:
            self._apply_collision_damage(collision_damage)
        
        # ===== ЗАГАЛЬНЕ ЗДОРОВ'Я =====
        self._calculate_overall_health()
    
    # ===== БАТАРЕЯ =====
    
    def _update_battery(self, energy_consumed: float, ambient_temp: float):
        """Оновити батарею"""
        
        # Розрядити батарею
        self.battery.discharge(energy_consumed)
        
        # Тепло від розрядження
        heat = energy_consumed * 0.5
        self.battery.apply_thermal_stress(heat)
        
        # Охолоджування
        cooling = (self.battery.temperature - ambient_temp) * 0.05
        self.battery.temperature = max(ambient_temp, self.battery.temperature - cooling)
        
        # Оновити здоров'я батареї
        self.battery.update_health()
    
    # ===== МОТОРИ =====
    
    def _update_motors(self, motor_stress: List[float], altitude: float, ambient_temp: float):
        """Оновити мотори"""
        
        for i, stress in enumerate(motor_stress):
            # Застосувати стрес
            self.motors.apply_stress(i, stress)
            
            # Охолоджування на висоті гірше
            motor = self.motors.motors[i]
            altitude_factor = 1 + (altitude / 20) * 0.3
            
            cooling = (motor['temperature'] - ambient_temp) * 0.03 / altitude_factor
            motor['temperature'] = max(ambient_temp, motor['temperature'] - cooling)
        
        # Оновити температури
        self.motors.update_temperatures()
    
    # ===== ДАТЧИКИ =====
    
    def _update_sensors(self, altitude: float, 
                       collision_occurred: bool, 
                       collision_damage: float):
        """Оновити датчики"""
        
        for i, sensor in enumerate(self.sensors.sensors):
            # Пил на низькій висоті
            if altitude <= 5:
                dust_factor = (5 - altitude) * 0.2
                self.sensors.apply_dirt(i, dust_factor * 0.1)
            
            # Забруднення від колізії
            if collision_occurred and collision_damage > 0:
                if sensor['type'] == 'camera':
                    dirt_amount = collision_damage * 20
                else:
                    dirt_amount = collision_damage * 10
                
                self.sensors.apply_dirt(i, dirt_amount)
    
    # ===== СТРУКТУРА =====
    
    def _apply_collision_damage(self, collision_damage: float):
        """Застосувати пошкодження від колізії"""
        
        # Розподілити пошкодження на компоненти
        propeller_damage = collision_damage * 30
        frame_damage = collision_damage * 20
        sensor_dirt = collision_damage * 25
        motor_stress_amount = collision_damage * 15
        thermal_stress = collision_damage * 10
        
        # Пошкодити пропелери
        for i in range(self.structure.num_propellers):
            self.structure.propeller_health[i] = max(
                0, 
                self.structure.propeller_health[i] - propeller_damage
            )
        
        # Пошкодити раму
        self.structure.integrity = max(0, self.structure.integrity - frame_damage)
        
        # Забруднити датчики
        for i in range(len(self.sensors.sensors)):
            self.sensors.apply_dirt(i, sensor_dirt)
        
        # Стрес на мотори
        for i in range(len(self.motors.motors)):
            self.motors.motors[i]['wear'] += motor_stress_amount
        
        # Тепловий стрес батареї
        self.battery.apply_thermal_stress(thermal_stress)
        
        # Записати в статистику
        self.structure.crash_count += 1
    
    # ===== ЗАГАЛЬНЕ ЗДОРОВ'Я =====
    
    def _calculate_overall_health(self):
        """Розрахувати загальне здоров'я"""
        
        battery_health = self.battery.health
        motor_health = self.motors.get_average_efficiency()
        sensor_health = self.sensors.get_average_accuracy()
        structure_health = self.structure.get_structural_integrity()
        
        overall = (
            battery_health * 0.3 +
            motor_health * 0.3 +
            sensor_health * 0.2 +
            structure_health * 0.2
        )
        
        self.health_history.append(overall)
    
    def get_overall_health(self) -> float:
        """Отримати поточне здоров'я (0-100)"""
        return self.health_history[-1] if self.health_history else 100.0
    
    def is_system_healthy(self) -> bool:
        """Чи система здорова?"""
        return (
            self.battery.is_healthy() and
            self.structure.is_flightworthy()
        )
    
    def get_critical_alerts(self) -> List[str]:
        """Отримати список критичних проблем"""
        alerts = []
        
        # Батарея
        if self.battery.temperature > 50:
            alerts.append("🔥 БАТАРЕЯ ПЕРЕГРІТА!")
        
        if self.battery.charge < 10:
            alerts.append("🔴 БАТАРЕЯ КРИТИЧНА!")
        
        # Мотори
        if any(m['temperature'] > 70 for m in self.motors.motors):
            alerts.append("🔥 МОТОРИ ПЕРЕГРІТІ!")
        
        # Структура
        if not self.structure.is_flightworthy():
            alerts.append("❌ ДРОН НЕ ПРИДАТНИЙ ДО ПОЛЬОТУ!")
        
        if self.structure.integrity < 30:
            alerts.append("💥 СТРУКТУРА КРИТИЧНА!")
        
        # Загальне здоров'я
        if self.get_overall_health() < 40:
            alerts.append("🚨 ЗАГАЛЬНЕ ЗДОРОВ'Я КРИТИЧНЕ!")
        
        return alerts
    
    def reset(self):
        """
        RESET HealthMonitor на початковий стан
        """
        
        self.health_history = []
        self.last_update = {
            'energy_consumed': 0,
            'motor_stress': [0, 0, 0, 0],
            'altitude': 0,
            'collision_occurred': False,
            'collision_damage': 0,
            'ambient_temp': 25
        }
        
        # Переінціалізувати здоров'я
        initial_health = (100 * 0.3 + 100 * 0.3 + 90 * 0.2 + 100 * 0.2)
        self.health_history = [initial_health]