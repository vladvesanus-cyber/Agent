"""
Адаптивний агент що балансує висоту, ризик, час та якість
"""

import numpy as np
from typing import Dict, Tuple


class AdaptiveHeightAgent:
    """
    Розумний агент який:
    1. Обирає оптимальну висоту на основі умов
    2. Балансує ризик поломки та якість дослідження
    3. Управляє часом та енергією
    4. Оцінює якість отриманої карти
    """
    
    def __init__(self, name: str = "AdaptiveHeightAgent"):
        self.name = name
        
        # Внутрішній стан
        self.world_map = {}
        self.visited_cells = set()
        self.frontier = set()
        
        # Параметри алгоритму
        self.quality_threshold = 0.7
        self.risk_tolerance = 0.5
        
        # Історія для навчання
        self.decision_history = []
    
    def decide(self, observation: Dict) -> Dict:
        """
        Прийняти рішення на основі багатьох факторів
        """
        
        # ===== КРОК 1: АНАЛІЗ ПОТОЧНОЇ СИТУАЦІЇ =====
        situation = self._analyze_situation(observation)
        
        # ===== КРОК 2: ВИБІР ОПТИМАЛЬНОЇ ВИСОТИ =====
        best_altitude = self._choose_optimal_altitude(situation)
        
        # ===== КРОК 3: ПЛАНУВАННЯ МАРШРУТУ =====
        direction = self._plan_direction(observation, best_altitude, situation)
        
        # ===== КРОК 4: РІШЕННЯ СКАНУВАТИ =====
        should_scan = self._should_scan(observation, situation)
        
        action = {
            'move': (direction[0], direction[1], best_altitude - observation['position'][2]),
            'scan': should_scan
        }
        
        # Запам'ятати рішення
        self.decision_history.append({
            'altitude': best_altitude,
            'direction': direction,
            'scan': should_scan
        })
        
        return action
    
    # ===== КРОК 1: АНАЛІЗ СИТУАЦІЇ =====
    
    def _analyze_situation(self, observation: Dict) -> Dict:
        """
        Повний аналіз поточної ситуації
        """
        
        health = observation['health']
        position = observation['position']
        battery = health['battery']['charge_percent']
        
        overall_health = health['overall_health']
        motor_health = np.mean([m['efficiency'] for m in health['motors']])
        sensor_accuracy = np.mean([s['accuracy'] for s in health['sensors']])
        structure_integrity = health['structure']['integrity']
        
        # Відстань до дому
        home_x, home_y = 15, 15
        dist_to_home = abs(position[0] - home_x) + abs(position[1] - home_y)
        
        # Енергія для повернення
        energy_needed_for_return = dist_to_home * 1.5
        energy_safety_margin = battery - energy_needed_for_return
        
        # Критичність
        is_critical = (
            battery < 25 or
            len(health['critical_alerts']) > 0 or
            overall_health < 40
        )
        
        situation = {
            'battery_percent': battery,
            'energy_safety_margin': energy_safety_margin,
            'is_critical': is_critical,
            'overall_health': overall_health,
            'motor_health': motor_health,
            'sensor_accuracy': sensor_accuracy,
            'structure_integrity': structure_integrity,
            'distance_to_home': dist_to_home,
            'position': position,
            'critical_alerts': health['critical_alerts'],
            'sensor_details': health['sensors'],
            'motor_details': health['motors']
        }
        
        return situation
    
    # ===== КРОК 2: ВИБІР ВИСОТИ =====
    
    def _choose_optimal_altitude(self, situation: Dict) -> float:
        """
        Вибрати оптимальну висоту (0-20)
        """
        
        best_altitude = 0
        best_score = -float('inf')
        
        for test_altitude in range(0, 21):
            score = self._evaluate_altitude(test_altitude, situation)
            
            if score > best_score:
                best_score = score
                best_altitude = test_altitude
        
        return float(best_altitude)
    
    def _evaluate_altitude(self, altitude: float, 
                          situation: Dict) -> float:
        """
        Оцінити якість польоту на цій висоті (-100 до 100)
        """
        
        # ===== ФАКТОР 1: ТОЧНІСТЬ ДАТЧИКІВ (30%) =====
        sensor_accuracy_factor = max(0, 100 - (altitude ** 1.5) * 2)
        sensor_score = sensor_accuracy_factor * 0.3
        
        # ===== ФАКТОР 2: РИЗИК ЗІТКНЕННЯ (20%) =====
        collision_risk = 1 - (altitude / 20)
        collision_score = (1 - collision_risk) * 0.2
        
        # ===== ФАКТОР 3: ЕНЕРГЕТИЧНА ВАРТІСТЬ (20%) =====
        energy_cost = 1 + (altitude / 10) ** 2
        energy_efficiency = 1 / energy_cost * 100
        energy_score = energy_efficiency * 0.2
        
        # ===== ФАКТОР 4: ЗАБРУДНЕННЯ ДАТЧИКІВ (15%) =====
        contamination_risk = max(0, (5 - altitude) * 0.2) if altitude < 5 else 0
        contamination_score = (1 - contamination_risk) * 0.15
        
        # ===== ФАКТОР 5: БЕЗПЕКА ДРОНА (15%) =====
        if situation['motor_health'] < 50:
            altitude_safety_score = (altitude / 20) * 15
        else:
            altitude_safety_score = 0
        
        total_score = (
            sensor_score +
            collision_score +
            energy_score +
            contamination_score +
            altitude_safety_score
        )
        
        # ===== ШТРАФИ ЗА КРИТИЧНІ УМОВИ =====
        if situation['is_critical']:
            total_score += altitude * 0.5
        
        if situation['energy_safety_margin'] < 20:
            total_score -= altitude * 0.3
        
        return total_score
    
    # ===== КРОК 3: ПЛАНУВАННЯ МАРШРУТУ =====
    
    def _plan_direction(self, observation: Dict, best_altitude: float, 
                       situation: Dict) -> Tuple[int, int]:
        """
        Вибрати напрямок руху (dx, dy)
        """
        
        # Якщо критично - йти додому
        if situation['is_critical']:
            return self._navigate_home(situation['position'])
        
        # Якщо мало енергії - почнемо повертатись
        if situation['energy_safety_margin'] < 30:
            return self._navigate_home(situation['position'])
        
        # Оцінити всі 4 напрямки
        best_direction = (0, 0)
        best_score = -float('inf')
        
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        
        for dx, dy in directions:
            score = self._evaluate_direction(
                (dx, dy),
                observation,
                situation,
                best_altitude
            )
            
            if score > best_score:
                best_score = score
                best_direction = (dx, dy)
        
        return best_direction
    
    def _evaluate_direction(self, direction: Tuple[int, int], 
                           observation: Dict, situation: Dict,
                           altitude: float) -> float:
        """
        Оцінити якість руху в цьому напрямку (-100 до 100)
        """
        
        dx, dy = direction
        new_x = situation['position'][0] + dx
        new_y = situation['position'][1] + dy
        
        # ===== ФАКТОР 1: ДОСЛІДЖЕННЯ =====
        is_new_cell = (new_x, new_y) not in self.visited_cells
        exploration_score = 50 if is_new_cell else 10
        
        # ===== ФАКТОР 2: РИЗИК ЗІТКНЕННЯ =====
        collision_risk = self._estimate_collision_risk(
            new_x, new_y, altitude, observation
        )
        safety_score = (1 - collision_risk) * 30
        
        # ===== ФАКТОР 3: ЯКІСТЬ ДОСЛІДЖЕННЯ =====
        sensor_accuracy = max(0, 100 - (altitude ** 1.5) * 2)
        quality_score = sensor_accuracy * 0.2
        
        # ===== ФАКТОР 4: ЕФЕКТИВНІСТЬ =====
        if (new_x, new_y) in self.visited_cells:
            efficiency_penalty = -20
        else:
            efficiency_penalty = 0
        
        total_score = (
            exploration_score +
            safety_score +
            quality_score +
            efficiency_penalty
        )
        
        return total_score
    
    def _estimate_collision_risk(self, x: float, y: float, altitude: float,
                                observation: Dict) -> float:
        """
        Оцінити ймовірність зіткнення (0-1)
        """
        
        if altitude > 10:
            return 0.1
        
        local_map = observation['local_map']
        
        if self._is_obstacle_nearby(x, y, local_map):
            collision_risk = 0.7
        else:
            collision_risk = 0.2
        
        altitude_factor = (5 - altitude) / 5 if altitude < 5 else 0
        total_risk = min(1.0, collision_risk + altitude_factor)
        
        return total_risk
    
    def _is_obstacle_nearby(self, x: float, y: float, local_map) -> bool:
        """Чи близько препятствие?"""
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                if local_map[dy + 2, dx + 2] != 0:
                    return True
        return False
    
    def _navigate_home(self, position: Tuple[float, float, float]) -> Tuple[int, int]:
        """Направитись додому"""
        x, y, z = position
        home_x, home_y = 15, 15
        
        if abs(x - home_x) > abs(y - home_y):
            return (1 if x < home_x else -1, 0)
        else:
            return (0, 1 if y < home_y else -1)
    
    # ===== КРОК 4: РІШЕННЯ СКАНУВАТИ =====
    
    def _should_scan(self, observation: Dict, situation: Dict) -> bool:
        """
        Чи варто сканувати на цьому кроці?
        """
        
        if situation['is_critical'] or situation['energy_safety_margin'] < 40:
            return False
        
        sensors = situation['sensor_details']
        avg_accuracy = np.mean([s['accuracy'] for s in sensors])
        avg_dirt = np.mean([s['dirt_level'] for s in sensors])
        
        if avg_dirt > 70:
            return False
        
        if avg_accuracy < 50:
            return False
        
        return situation['energy_safety_margin'] > 30