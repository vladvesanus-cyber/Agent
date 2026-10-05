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
        """
        Розпізнати та повернути дію
        
        Режими:
        1. ДОСЛІДЖЕННЯ (батарея > 30%) - нормально розглядаємо карту
        2. ПОВЕРНЕННЯ ДОДОМУ (батарея < 30%) - агресивно летимо домой
        """
        
        try:
            situation = self._analyze_situation(observation)
            
            # ===== ВИЗНАЧИТИ РЕЖИМ =====
            battery = situation['battery']
            home_mode = battery < 30  # ← РЕЖИМ ПОВЕРНЕННЯ ДОДОМУ
            
            # ===== ОБРАТИ ВИСОТУ =====
            if home_mode:
                # На поверненні - низька висота для економії
                optimal_altitude = 2.0
            else:
                # Нормальне дослідження
                optimal_altitude = self._choose_altitude(situation)
            
            # ===== ОБРАТИ НАПРЯМОК =====
            if home_mode:
                # Летимо ДОДОМУ для перезарядки (огинаючи перешкоди!)
                next_move = self._go_home_direction(observation, situation)
            else:
                # Нормальне дослідження
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
        """Вибрати оптимальну висоту для АКТИВНОГО ДОСЛІДЖЕННЯ"""
        
        local_obs = situation['local_obstacles']
        battery = situation['battery']
        sensor_dirt = situation['sensor_dirt']
        overall_health = situation['overall_health']
        
        # ===== КРИТИЧНІ УМОВИ =====
        if overall_health < 30 or not situation['is_flightworthy']:
            return 0.0
        
        # ===== ВОДА НИЖЧЕ =====
        if local_obs['has_water_below']:
            return 8.0  # Достатньо щоб уникнути води
        
        # ===== ДАТЧИКИ ЗАБРУДНЕНІ =====
        if sensor_dirt > 60:
            return 9.0
        elif sensor_dirt > 40:
            return 7.0
        
        # ===== БАТАРЕЯ КРИТИЧНА =====
        if battery < 15:
            return 1.0  # Мінімальна висота
        
        # ===== БАТАРЕЯ НИЗЬКА =====
        if battery < 30:
            return 3.0  # Економна висота
        
        # ===== МОТОРИ ГАРЯЧІ =====
        if situation['motor_temp'] > 60:
            return 10.0  # Охолодження
        elif situation['motor_temp'] > 50:
            return 8.0
        
        # ===== АКТИВНЕ ДОСЛІДЖЕННЯ З ДЕРЕВАМИ =====
        # Літати ВИЩЕ щоб переходити через дерева
        if local_obs['has_trees_around']:
            return 6.5  # ← Вище, щоб пройти мимо деревьев
        
        # ===== НОРМАЛЬНЕ ДОСЛІДЖЕННЯ =====
        # Літати помірно високо для кращої видимості
        return 6.0
    
    def _choose_direction(self, observation: Dict, situation: Dict) -> tuple:
        """
        Вибрати напрямок руху - РОЗУМНА СТРАТЕГІЯ
        
        ПРІОРИТЕТИ:
        1. Нові клітини БЕЗ перешкод (безпечні) ← МАКСИМУМ
        2. Відвідані БЕЗ перешкод (для різноманітності)
        3. Нові клітини ЧЕРЕЗ дерева ← АГРЕСИВНО ЛИШЕ ЯК КРАЙНІЙ ЗАСІБ
        4. Відвідані через дерева (останній засіб)
        """
        
        position = observation['position']
        visited_cells = observation['visited_cells']
        local_obs = situation['local_obstacles']
        local_map = observation['local_map']
        
        if not isinstance(visited_cells, set):
            visited_cells = set()
        
        # ===== ЕКСТРЕНА УМОВА =====
        if situation['overall_health'] < 20 or situation['battery'] < 5:
            return self._go_away_direction(position)
        
        # ===== ВСІ НАПРЯМКИ =====
        directions = [
            (1, 0, 0),    # Вправо
            (-1, 0, 0),   # Вліво
            (0, 1, 0),    # Вниз
            (0, -1, 0),   # Вгору
        ]
        
        center = local_map.shape[0] // 2
        altitude = situation['current_altitude']
        
        # ===== КАТЕГОРИЗУВАТИ НАПРЯМКИ =====
        safe_new = []         # ПРІОРИТЕТ 1: Нові БЕЗПЕЧНІ клітини
        safe_old = []         # ПРІОРИТЕТ 2: Старі БЕЗПЕЧНІ клітини
        risky_new = []        # ПРІОРИТЕТ 3: Нові РИЗИКОВАНІ (дерева)
        risky_old = []        # ПРІОРИТЕТ 4: Старі РИЗИКОВАНІ
        
        for dx, dy, dz in directions:
            local_x = center + dx
            local_y = center + dy
            
            if 0 <= local_x < local_map.shape[1] and 0 <= local_y < local_map.shape[0]:
                cell_value = local_map[local_y, local_x]
                
                # ===== ГРАНИЦЯ КАРТИ - ЗАБОРОНЬЕНО =====
                if cell_value == -1:
                    continue
                
                cell_int = int(cell_value)
                
                # ===== ВИЗНАЧИТИ ЧИ БЕЗПЕЧНО =====
                is_safe = False
                if cell_int == 0:  # FREE
                    is_safe = True
                elif cell_int == 3 and altitude >= 5:  # WATER на висоті
                    is_safe = True
                elif cell_int == 4 and altitude >= 5:  # MOUNTAIN на висоті
                    is_safe = True
                
                # ===== ВИЗНАЧИТИ ЧИ НОВА КЛІТИНА =====
                new_x = position[0] + dx
                new_y = position[1] + dy
                cell_coord = (int(new_x), int(new_y))
                is_new = cell_coord not in visited_cells
                
                # ===== РОЗПОДІЛИТИ ПО КАТЕГОРІЯМ =====
                if is_safe:
                    if is_new:
                        safe_new.append((dx, dy, dz))
                    else:
                        safe_old.append((dx, dy, dz))
                else:
                    # Ризиковано - через дерева
                    if cell_int == 2 and altitude >= 2:  # TREE на висоті
                        if is_new:
                            risky_new.append((dx, dy, dz))
                        else:
                            risky_old.append((dx, dy, dz))
        
        # ===== ВИБРАТИ ПО ПРІОРИТЕТУ =====
        
        # ПРІОРИТЕТ 1: Нові БЕЗПЕЧНІ клітини ← МАКСИМУМ ПРІОРИТЕТУ
        if safe_new:
            best_direction = random.choice(safe_new)
            return best_direction
        
        # ПРІОРИТЕТ 2: Старі БЕЗПЕЧНІ (для різноманітності, коли нема нових)
        if safe_old:
            best_direction = random.choice(safe_old)
            return best_direction
        
        # ПРІОРИТЕТ 3: Нові ЧЕРЕЗ ДЕРЕВА (агресивно, але лише якщо нема альтернативи!)
        if risky_new:
            print(f"   ⚠️  АГРЕСИВНО: Немає безпечних нових клеток! Летимо через дерева...")
            best_direction = random.choice(risky_new)
            return best_direction
        
        # ПРІОРИТЕТ 4: Старі ЧЕРЕЗ ДЕРЕВА (останній засіб)
        if risky_old:
            print(f"   ⚠️⚠️  КРИТИЧНА СИТУАЦІЯ: Летимо через дерева у старих місцях...")
            best_direction = random.choice(risky_old)
            return best_direction
        
        # ПРІОРИТЕТ 5: Нічого не залишилось - відійти від границі
        return self._go_away_from_boundary(position, local_obs, local_map)
    
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
    
    def _go_home_direction(self, observation: Dict, situation: Dict) -> tuple:
        """
        Напрямок ДОДОМУ (на базу для перезарядки) - ОГИНАЄ ПЕРЕШКОДИ.

        Раніше цей метод просто летів прямо на (15, 15), ігноруючи
        local_map - через це дрон міг врізатись у перешкоду/дерево на
        шляху додому і розбитись, замість долетіти і перезарядитись.
        Тепер він, як і _choose_direction, дивиться на vnemy (local_map)
        і з безпечних напрямків обирає той, що найбільше наближає
        до справжньої домашньої позиції (observation['home_position']).
        """
        position = observation['position']
        x, y, z = position
        home_x, home_y = observation.get('home_position', (x, y))
        local_map = observation['local_map']
        center = local_map.shape[0] // 2
        altitude = situation['current_altitude']

        directions = [
            (1, 0, 0),
            (-1, 0, 0),
            (0, 1, 0),
            (0, -1, 0),
        ]

        safe_candidates = []  # (нова_дистанція_до_дому, напрямок)

        for dx, dy, dz in directions:
            local_x = center + dx
            local_y = center + dy

            if not (0 <= local_x < local_map.shape[1] and 0 <= local_y < local_map.shape[0]):
                continue

            cell_value = local_map[local_y, local_x]
            if cell_value == -1:  # границя карти
                continue

            cell_int = int(cell_value)

            # ===== БЕЗПЕКА - ВІДПОВІДНО ДО СПРАВЖНЬОЇ ФІЗИКИ environment.py =====
            # environment.detect_collision(): на висоті z <= 1 блокує ВСЕ
            # (перешкода/вода/гора/дерево). На висоті z > 1 перешкода/вода/гора
            # взагалі НЕ становлять загрози - ризик лишається тільки у дерев
            # (гілки, ймовірнісно). Раніше тут перешкода вважалась небезпечною
            # на будь-якій висоті - через це дрон на шляху додому міг
            # "вважати" прохідну клітину заблокованою і застрягати, гойдаючись
            # між двома клітинками замість летіти далі.
            if cell_int == 0:  # FREE
                is_safe = True
            elif altitude > 1:  # вище 1м - перешкода/вода/гора/дерево прохідні
                is_safe = True
            else:
                is_safe = False

            if not is_safe:
                continue

            new_distance = abs((x + dx) - home_x) + abs((y + dy) - home_y)
            safe_candidates.append((new_distance, (dx, dy, dz)))

        if safe_candidates:
            # Обрати напрямок, що найбільше наближає до дому
            safe_candidates.sort(key=lambda c: c[0])
            return safe_candidates[0][1]

        # ===== НІЧОГО БЕЗПЕЧНОГО В БІК ДОМУ - ХОЧ БИ РУХАТИСЬ =====
        for dx, dy, dz in directions:
            local_x = center + dx
            local_y = center + dy
            if (0 <= local_x < local_map.shape[1] and 0 <= local_y < local_map.shape[0]
                    and local_map[local_y, local_x] != -1):
                return (dx, dy, dz)

        # ===== ОСТАННІЙ ЗАСІБ - ПІДНЯТИСЬ ВИЩЕ =====
        return (0, 0, 1)