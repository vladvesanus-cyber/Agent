"""
AdaptiveHeightAgent - розумний агент що вчиться без знання про карту
"""

import numpy as np
import random
from typing import Dict, Set, Tuple


class AdaptiveHeightAgent:
    """
    Агент що адаптивно дослідує невідому територію
    Не знає розміри карти - вчиться на основі сенсорів і колізій
    """
    
    def __init__(self):
        self.boundary_cells = set()  # Клітини де дрон ударився або виявив границю
        self.safe_directions = {}     # Напрямки що не приводили до колізій
        self.stuck_count = 0
        self.last_position = None
    
    def decide(self, observation: Dict) -> Dict:
        """Розпізнати та повернути дію"""
        
        try:
            situation = self._analyze_situation(observation)
            optimal_altitude = self._choose_altitude(situation)
            next_move = self._choose_direction(observation, situation)
            
            self.last_position = observation['position']
            
            return {
                'move': next_move,
                'altitude': optimal_altitude
            }
        
        except Exception as e:
            print(f"❌ ПОМИЛКА В АГЕНТІ: {e}")
            raise
    
    def _analyze_situation(self, observation: Dict) -> Dict:
        """Проаналізувати ситуацію"""
        
        health = observation['health']
        position = observation['position']
        local_map = observation['local_map']
        
        # ===== БАТАРЕЯ =====
        battery = health['battery']['charge_percent']
        battery_temp = health['battery']['temperature']
        
        # ===== МОТОРИ =====
        motors = health['motors']
        motor_health = np.mean([m['efficiency'] for m in motors])
        motor_temp = np.mean([m['temperature'] for m in motors])
        
        # ===== ДАТЧИКИ =====
        sensors = health['sensors']
        sensor_accuracy = np.mean([s['accuracy'] for s in sensors])
        sensor_dirt = np.mean([s['dirt_level'] for s in sensors])
        
        # ===== СТРУКТУРА =====
        structure = health['structure']
        integrity = structure['integrity']
        is_flightworthy = structure['is_flightworthy']
        
        # ===== ЗАГАЛЬНЕ ЗДОРОВ'Я =====
        overall_health = health['overall_health']
        critical_alerts = health['critical_alerts']
        
        # ===== АНАЛІЗ ЛОКАЛЬНОЇ КАРТИ =====
        local_obs = self._analyze_local_map(local_map, position)
        
        situation = {
            'battery': battery,
            'battery_temp': battery_temp,
            'motor_health': motor_health,
            'motor_temp': motor_temp,
            'sensor_accuracy': sensor_accuracy,
            'sensor_dirt': sensor_dirt,
            'structure_integrity': integrity,
            'is_flightworthy': is_flightworthy,
            'overall_health': overall_health,
            'has_critical_alerts': len(critical_alerts) > 0,
            'critical_alerts': critical_alerts,
            'exploration': observation['exploration_ratio'],
            'position': position,
            'local_map': local_map,
            'local_obstacles': local_obs,
            'current_altitude': position[2],
            'step_count': observation['step_count']
        }
        
        return situation
    
    def _analyze_local_map(self, local_map: np.ndarray, position: tuple) -> Dict:
        """
        Проаналізувати локальну карту
        -1 = границя карти!
        """
        
        has_water_below = False
        has_obstacles_around = False
        has_trees_around = False
        boundary_directions = []  # Напрямки на границю
        
        center = local_map.shape[0] // 2
        
        # Перевіряємо всю локальну карту
        for dy in range(-center, center+1):
            for dx in range(-center, center+1):
                y = center + dy
                x = center + dx
                
                if 0 <= y < local_map.shape[0] and 0 <= x < local_map.shape[1]:
                    cell = local_map[y, x]
                    
                    # ===== ГРАНИЦЯ КАРТИ =====
                    if cell == -1:
                        if dx != 0 or dy != 0:  # Не в центрі
                            boundary_directions.append((dx, dy))
                        continue
                    
                    cell = int(cell)
                    
                    # ===== ВОДА НИЖЧЕ =====
                    if cell == 3 and dy == 0 and dx == 0:
                        has_water_below = True
                    
                    # ===== ПЕРЕШКОДИ =====
                    if cell == 1:  # OBSTACLE
                        has_obstacles_around = True
                    if cell == 2:  # TREE
                        has_obstacles_around = True
                        has_trees_around = True
        
        return {
            'has_water_below': has_water_below,
            'has_obstacles_around': has_obstacles_around,
            'has_trees_around': has_trees_around,
            'boundary_directions': boundary_directions
        }
    
    def _choose_altitude(self, situation: Dict) -> float:
        """Вибрати оптимальну висоту"""
        
        local_obs = situation['local_obstacles']
        battery = situation['battery']
        sensor_dirt = situation['sensor_dirt']
        overall_health = situation['overall_health']
        
        # ===== КРИТИЧНІ УМОВИ =====
        if overall_health < 40 or not situation['is_flightworthy']:
            return 0.0
        
        # ===== ВОДА НИЖЧЕ =====
        if local_obs['has_water_below']:
            return 10.0
        
        # ===== ДАТЧИКИ ЗАБРУДНЕНІ =====
        if sensor_dirt > 60:
            return 10.0
        elif sensor_dirt > 40:
            return 8.0
        
        # ===== БАТАРЕЯ НИЗЬКА =====
        if battery < 20:
            return 2.0
        
        # ===== МОТОРИ ГАРЯЧІ =====
        if situation['motor_temp'] > 60:
            return 12.0
        elif situation['motor_temp'] > 50:
            return 9.0
        
        # ===== ДЕРЕВА НАВКОЛО =====
        if local_obs['has_trees_around']:
            return 7.0
        
        # ===== НОРМАЛЬНО =====
        return 5.5
    
    def _choose_direction(self, observation: Dict, situation: Dict) -> tuple:
        """
        Вибрати напрямок руху
        Уникати границь на основі локальної карти
        """
        
        position = observation['position']
        visited_cells = observation['visited_cells']
        local_obs = situation['local_obstacles']
        local_map = observation['local_map']
        
        if not isinstance(visited_cells, set):
            visited_cells = set()
        
        # ===== КРИТИЧНІ УМОВИ =====
        if situation['overall_health'] < 40 or situation['battery'] < 15:
            return self._go_away_direction(position)
        
        # ===== ВСІ НАПРЯМКИ =====
        directions = [
            (1, 0, 0),    # Вправо
            (-1, 0, 0),   # Вліво
            (0, 1, 0),    # Вниз
            (0, -1, 0),   # Вгору
        ]
        
        # ===== УНИКАТИ ГРАНИЦЬ НА ОСНОВІ ЛОКАЛЬНОЇ КАРТИ =====
        valid_directions = []
        center = local_map.shape[0] // 2
        
        for dx, dy, dz in directions:
            # Перевірити що в цьому напрямку в локальній карті
            local_x = center + dx
            local_y = center + dy
            
            # Чи це границя карти?
            if 0 <= local_x < local_map.shape[1] and 0 <= local_y < local_map.shape[0]:
                cell_value = local_map[local_y, local_x]
                if cell_value != -1:  # Не границя
                    valid_directions.append((dx, dy, dz))
            else:
                # За межами локальної карти - це точно границя
                pass
        
        # Якщо близько до границі - спробуємо відійти від найближчої границі
        if not valid_directions:
            # Вибрати напрямок з найменшою кількістю границь
            return self._go_away_from_boundary(position, local_obs, local_map)
        
        # ===== ВИБРАТИ НАЙКРАЩИЙ НАПРЯМОК =====
        best_direction = None
        best_score = -1
        
        for dx, dy, dz in valid_directions:
            new_x = position[0] + dx
            new_y = position[1] + dy
            cell_coord = (int(new_x), int(new_y))
            
            # Нові клітини - приоритет 100
            if cell_coord not in visited_cells:
                score = 100
            else:
                score = 10
            
            if score > best_score:
                best_score = score
                best_direction = (dx, dy, dz)
        
        if best_direction is None:
            best_direction = random.choice(valid_directions) if valid_directions else (0, 0, 0)
        
        return best_direction
    
    def _go_away_from_boundary(self, position: tuple, local_obs: Dict, local_map: np.ndarray) -> tuple:
        """Рухатись ВІД найближчої границі"""
        
        center = local_map.shape[0] // 2
        
        # Знайти напрямки без границь
        safe_directions = []
        
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                    
                local_x = center + dx
                local_y = center + dy
                
                if (0 <= local_x < local_map.shape[1] and 
                    0 <= local_y < local_map.shape[0]):
                    cell = local_map[local_y, local_x]
                    if cell != -1:  # Не границя
                        safe_directions.append((dx, dy, 0))
        
        if safe_directions:
            return random.choice(safe_directions)
        else:
            # Останній засіб - літати вгору
            return (0, 0, 1)
    
    def _go_away_direction(self, position: tuple) -> tuple:
        """Напрямок ВІД границі - випадковий"""
        
        directions = [
            (1, 0, 0),
            (-1, 0, 0),
            (0, 1, 0),
            (0, -1, 0),
        ]
        
        return random.choice(directions)