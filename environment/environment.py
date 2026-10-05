"""
Drone Environment - один клас з параметризацією через конфіги
"""

import numpy as np
from typing import Dict, Tuple
from enum import Enum


class Terrain(Enum):
    FREE = 0
    OBSTACLE = 1
    TREE = 2
    WATER = 3
    MOUNTAIN = 4


class DroneEnvironment:
    """
    Один environment який налаштовується через конфіги
    """
    
    def __init__(self, config: Dict):
        """
        Args:
            config: Конфігурація (зі словника YAML)
                ├── map: width, height
                ├── terrain: obstacle_ratio, tree_ratio, ...
                ├── drone: start_x, start_y, battery_capacity, ...
                ├── physics: energy_base_cost, altitude_multiplier, ...
                ├── collision: detection_enabled, damages, ...
                └── episode: max_steps, seed
        """
        
        # ===== НАЛАШТУВАННЯ ІЗ КОНФІГА =====
        
        # Карта
        self.width = config['map']['width']
        self.height = config['map']['height']
        
        # Терен
        self.obstacle_ratio = config['terrain']['obstacle_ratio']
        self.tree_ratio = config['terrain']['tree_ratio']
        self.water_ratio = config['terrain']['water_ratio']
        self.mountain_ratio = config['terrain']['mountain_ratio']
        
        # Дрон
        self.start_x = config['drone']['start_x']
        self.start_y = config['drone']['start_y']
        self.start_z = config['drone'].get('start_z', 0)
        self.battery_capacity = config['drone']['battery_capacity']
        self.max_altitude = config['drone']['max_altitude']
        
        # Фізика
        self.energy_base_cost = config['physics']['energy_base_cost']
        self.altitude_multiplier_enabled = config['physics']['altitude_multiplier']
        self.sensor_accuracy_decline = config['physics']['sensor_accuracy_decline']
        
        # Колізія
        self.collision_detection = config['collision']['detection_enabled']
        self.tree_damage = config['collision']['tree_collision_damage']
        self.obstacle_damage = config['collision']['obstacle_collision_damage']

         # ===== COLLISION DETECTION =====
        self.collision_log = []
        self.last_collision = None
        
        # Спостереження
        self.observation_radius = config['observation']['radius']
        self.include_health = config['observation']['include_health']

        # ===== КВАЛІТА СКАНУВАННЯ (ЗАЛЕЖНО ВІД ВИСОТИ) =====
        # Занадто низько: пилюка/трава біля землі заважає сенсорам.
        # Занадто високо: гірша роздільна здатність сенсора.
        # В "хорошому" діапазоні - скан на 100%, за межами - лінійно падає до 0.
        self.min_good_altitude = config['observation'].get('min_good_altitude', 2.0)
        self.max_good_altitude = config['observation'].get('max_good_altitude', 10.0)
        self.min_scan_quality = config['observation'].get('min_scan_quality', 50.0)
        
        # Епізод
        self.max_steps = config['episode']['max_steps']
        self.seed = config['episode']['seed']
        
        # ===== ІНІЦІАЛІЗАЦІЯ =====
        
        np.random.seed(self.seed)
        
        # Генерувати карту
        self.world_map = self._generate_map()
        self.drone_knowledge = np.zeros((self.height, self.width))
        
        # Стан дрона
        self.drone_x = self.start_x
        self.drone_y = self.start_y
        self.drone_z = self.start_z
        self.visited_cells = {(self.drone_x, self.drone_y)}
        
        # Лічильник кроків
        self.step_count = 0
        
        # Логи
        self.collision_log = []
        
        print(f"✅ Environment створений:")
        print(f"   Розмір карти: {self.width}×{self.height}")
        print(f"   Препятствів: {self.obstacle_ratio*100:.0f}%")
        print(f"   Батарея дрона: {self.battery_capacity}%")
        print(f"   Видимість: {self.observation_radius*2+1}×{self.observation_radius*2+1}")
    
    # ===== ГЕНЕРАЦІЯ КАРТИ =====
    
    def _generate_map(self) -> np.ndarray:
        """
        Генерувати карту на основі конфіга
        """
        terrain = np.full((self.height, self.width), Terrain.FREE.value)
        
        # Препятствия
        num_obstacles = int(self.width * self.height * self.obstacle_ratio)
        for _ in range(num_obstacles):
            x = np.random.randint(0, self.width)
            y = np.random.randint(0, self.height)
            terrain[y, x] = Terrain.OBSTACLE.value
        
        # Дерева
        num_trees = int(self.width * self.height * self.tree_ratio)
        for _ in range(num_trees):
            x = np.random.randint(0, self.width)
            y = np.random.randint(0, self.height)
            terrain[y, x] = Terrain.TREE.value
        
        # Вода
        num_water = int(self.width * self.height * self.water_ratio)
        for _ in range(num_water):
            x = np.random.randint(0, self.width)
            y = np.random.randint(0, self.height)
            terrain[y, x] = Terrain.WATER.value
        
        # Гори
        num_mountains = int(self.width * self.height * self.mountain_ratio)
        for _ in range(num_mountains):
            x = np.random.randint(0, self.width)
            y = np.random.randint(0, self.height)
            terrain[y, x] = Terrain.MOUNTAIN.value

        # ===== ОЧИСТИТИ БАЗУ (СТАРТ/ДОМ) ВІД ПЕРЕШКОД =====
        # Випадкова генерація вище може покласти перешкоду/дерево/воду/гору
        # прямо на стартову клітину дрона. Тоді дрон не може навіть
        # піднятись з місця (на землі все блокує), а при поверненні додому
        # для перезарядки ця ж клітина завжди лишається "небезпечною".
        # База має бути гарантовано вільною - чистимо саму клітину й
        # найближчі сусідні (щоб було куди сісти навіть при невеликому зносі).
        for hy in range(max(0, self.start_y - 1), min(self.height, self.start_y + 2)):
            for hx in range(max(0, self.start_x - 1), min(self.width, self.start_x + 2)):
                terrain[hy, hx] = Terrain.FREE.value

        return terrain
    
    # ===== СИМУЛЯЦІЯ =====
    
    def step(self, action: Dict) -> Tuple[Dict, float, bool]:
        """
        Один крок симуляції
        """
        
        self.step_count += 1
        
        # Розраховуємо енергію на основі конфіга
        energy_cost = self._calculate_energy_cost(action)
        
        # Рухаємо дрона
        dx, dy, dz = action['move']
        new_x = self.drone_x + dx
        new_y = self.drone_y + dy
        new_z = self.drone_z + dz
        
        # Перевіряємо границі
        if not (0 <= new_x < self.width and 0 <= new_y < self.height):
            reward = -50
            done = True
            observation = self._get_observation()
            return observation, reward, done
        
        # Перевіряємо висоту
        if not (0 <= new_z <= self.max_altitude):
            reward = -50
            done = True
            observation = self._get_observation()
            return observation, reward, done

        # ===== ПЕРЕВІРИТИ КОЛІЗІЮ =====
        if self.detect_collision(new_x, new_y, new_z):
            # Є колізія!
            terrain = self.classify_terrain(new_x, new_y)
            damage = self.calculate_collision_damage(terrain, self.drone_z)
            
            # Записати в лог
            self.report_collision(terrain, damage, new_x, new_y, new_z)
            
            # Повернути інформацію про колізію
            observation = self.get_observation()
            observation['collision'] = {
                'occurred': True,
                'terrain_type': terrain,
                'damage': damage
            }
            
            return observation, -50 * damage, True  # Цикл закінчується
        
        # Оновлюємо позицію
        self.drone_x = new_x
        self.drone_y = new_y
        self.drone_z = new_z
        self.visited_cells.add((int(self.drone_x), int(self.drone_y)))
        
        # Розраховуємо нагороду
        exploration_ratio = len(self.visited_cells) / (self.width * self.height)
        
        reward = (
            exploration_ratio * 100 +        # За дослідження
            (50 if self._is_home() else 0) +  # За повернення
            - energy_cost * 2 -               # За енергію
            - self.step_count * 0.1           # За час
        )
        
        # Умова завершення
        done = (self.step_count >= self.max_steps or 
                exploration_ratio > 0.8 or
                not self._is_drone_flyable())
        
        observation = self.get_observation()
        observation['collision'] = {'occurred': False}
        
        return observation, reward, done
    
    # ===== ДОПОМІЖНІ МЕТОДИ =====
    
    def _calculate_energy_cost(self, action: Dict) -> float:
        """
        Розрахувати енергію на основі конфіга
        """
        dx, dy, dz = action['move']
        
        # Базова вартість руху
        distance = abs(dx) + abs(dy)
        cost = distance * self.energy_base_cost
        
        # Вартість висоти
        if self.altitude_multiplier_enabled:
            altitude_multiplier = 1 + (self.drone_z / 10) ** 2
            cost *= altitude_multiplier
        
        # Вартість зміни висоти
        cost += abs(dz) * 0.5
        
        return cost
    
    def get_observation(self) -> Dict:
        """Отримати спостереження про світ"""
        
        local_map = self.get_local_map()
        
        observation = {
            'position': (self.drone_x, self.drone_y, self.drone_z),
            'local_map': local_map,
            'exploration_ratio': len(self.visited_cells) / (self.width * self.height),
            'visited_cells': len(self.visited_cells),
            'sensor_accuracy': self.calculate_sensor_accuracy(self.drone_z),
            'step_count': self.step_count
        }
        
        return observation
    
    def get_local_map(self) -> np.ndarray:
        """
        Локальна карта на основі radius з конфіга
        За межами карти = -1 (границя!)
        """
        local = np.full((2*self.observation_radius+1, 2*self.observation_radius+1), -1, dtype=float)
        
        for dy in range(-self.observation_radius, self.observation_radius+1):
            for dx in range(-self.observation_radius, self.observation_radius+1):
                y = int(self.drone_y) + dy
                x = int(self.drone_x) + dx
                
                if 0 <= x < self.width and 0 <= y < self.height:
                    local[dy+self.observation_radius, dx+self.observation_radius] = self.world_map[y, x]
                else:
                    # За межами карти -境界 (границя)
                    local[dy+self.observation_radius, dx+self.observation_radius] = -1
        
        return local
    
    def calculate_scan_quality(self, altitude: float) -> float:
        """
        Kvalita skenu zavisi od vysky letu (0-100):

        - Pod min_good_altitude: dron je prilis nizko - prach, trava a
          okolite prekazky rusia senzory. Kvalita klesa linearne k 0 na
          samotnej zemi (z=0).
        - V pasme [min_good_altitude, max_good_altitude]: idealna vyska,
          plna kvalita (100 %).
        - Nad max_good_altitude: klesajuce rozlisenie senzora. Kvalita
          klesa linearne k 0 pri max_altitude.
        """
        if altitude < self.min_good_altitude:
            span = max(self.min_good_altitude, 1e-6)
            return max(0.0, min(100.0, (altitude / span) * 100.0))

        if altitude > self.max_good_altitude:
            span = max(self.max_altitude - self.max_good_altitude, 1e-6)
            return max(0.0, 100.0 - (altitude - self.max_good_altitude) / span * 100.0)

        return 100.0

    def is_scan_good(self, altitude: float) -> bool:
        """Chi je sken na danej vyske dost kvalitny na to, aby sa bunka ratala ako preskumana?"""
        return self.calculate_scan_quality(altitude) >= self.min_scan_quality

    def _get_health_info(self) -> Dict:
        """Placeholder для health інформації"""
        return {}
    
    def _is_home(self) -> bool:
        """Чи дрон дома?"""
        return (self.drone_x == self.start_x and 
                self.drone_y == self.start_y)
    
    def _is_drone_flyable(self) -> bool:
        """Чи дрон ще може летіти?"""
        return True  # Буде заповнено з drone.health_monitor
    
    def reset(self) -> Dict:
        """Перезавантажити епізод"""
        self.drone_x = self.start_x
        self.drone_y = self.start_y
        self.drone_z = self.start_z
        self.visited_cells = {(self.drone_x, self.drone_y)}
        self.step_count = 0
        self.collision_log = []
        
        return self._get_observation()

    def detect_collision(self, x: float, y: float, z: float) -> bool:
        """
        Чи буде колізія на цій позиції?
        
        Проверяет:
        - Границы карты
        - Препятствия на земле
        - Деревья на высоте
        """
        
        # ===== ПЕРЕВІРИТИ ГРАНИЦІ КАРТИ =====
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return True  # За межами карти - колізія!
        
        # ===== ПЕРЕВІРИТИ ВИСОТУ =====
        if z < 0 or z > self.max_altitude:
            return True
        
        # ===== НА ЗЕМЛІ (z <= 1) - ВСЕ ПЕРЕШКОДЖАЄ =====
        if z <= 1:
            cell = int(self.world_map[int(y), int(x)])
            
            if cell == Terrain.OBSTACLE.value:
                return True  # Стіна
            if cell == Terrain.WATER.value:
                return True  # Вода
            if cell == Terrain.MOUNTAIN.value:
                return True  # Гора
            if cell == Terrain.TREE.value:
                return True  # Дерево на землі
        
        # ===== НА ВИСОТІ (1 < z <= max_altitude) =====
        elif z > 1:
            cell = int(self.world_map[int(y), int(x)])
            
            # Тільки дерева мають гілки
            if cell == Terrain.TREE.value:
                return np.random.random() < 0.3
            elif cell == Terrain.MOUNTAIN.value:
                return True  # Гори можуть мати виступи
            
            return False
        
        return False

    def classify_terrain(self, x: float, y: float) -> str:
        """
        Розпізнати тип терену
        """
        
        if not (0 <= x < self.width and 0 <= y < self.height):
            return "out_of_bounds"
        
        cell = self.world_map[int(y), int(x)]
        
        terrain_map = {
            Terrain.OBSTACLE.value: "hard_obstacle",
            Terrain.TREE.value: "tree_branches",
            Terrain.WATER.value: "water",
            Terrain.MOUNTAIN.value: "mountain",
            Terrain.FREE.value: "free"
        }
        
        return terrain_map.get(cell, "unknown")

    def calculate_collision_damage(self, terrain_type: str, altitude: float) -> float:
        """
        Розрахувати пошкодження від колізії
        
        Логіка:
        - На землі: максимальне пошкодження
        - На висоті: мінімальне (спускаємось повільно)
        - Вода: критична на землі, не впливає на висоті
        """
        
        # Базове пошкодження за типом
        damage_map = {
            'hard_obstacle': 1.0,
            'tree_branches': 0.3,
            'mountain': 0.5,
            'water': 0.8,
            'out_of_bounds': 1.0,
            'free': 0.0
        }
        
        base_damage = damage_map.get(terrain_type, 0.0)
        
        if base_damage == 0:
            return 0.0
        
        # На низькій висоті пошкодження серйозніше
        # На висоті > 5м - пошкодження мінімальне
        if altitude <= 1:
            altitude_factor = 1.5  # 150% пошкодження на землі
        elif altitude <= 3:
            altitude_factor = 1.2  # 120%
        elif altitude <= 5:
            altitude_factor = 0.8  # 80%
        else:
            altitude_factor = 0.2  # Мінімум на висоті
        
        total_damage = base_damage * altitude_factor
        return min(1.0, total_damage)
    
    def get_danger_zones_around(self, x: float, y: float, radius: int = 3) -> list:
        """
        Отримати небезпечні зони навколо позиції
        Замість: CollisionDetector.get_danger_zones_around()
        """
        
        danger_zones = []
        
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx = x + dx
                ny = y + dy
                
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    cell = self.world_map[int(ny), int(nx)]
                    if cell != Terrain.FREE.value:
                        danger_zones.append({
                            'x': nx,
                            'y': ny,
                            'type': self.classify_terrain(nx, ny)
                        })
        
        return danger_zones
    
    def report_collision(self, terrain_type: str, damage: float, 
                        x: float, y: float, z: float) -> Dict:
        """
        Записати колізію в лог
        Замість: CollisionDetector.report_collision()
        """
        
        collision_event = {
            'position': (x, y, z),
            'terrain_type': terrain_type,
            'damage': damage,
            'timestamp': len(self.collision_log)
        }
        
        self.last_collision = collision_event
        self.collision_log.append(collision_event)
        
        return collision_event