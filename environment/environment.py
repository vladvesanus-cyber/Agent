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
    
    def __init__(self, config: Dict):
        
        # Map
        self.width = config['map']['width']
        self.height = config['map']['height']
        
        # Obstacles
        self.obstacle_ratio = config['terrain']['obstacle_ratio']
        self.tree_ratio = config['terrain']['tree_ratio']
        self.water_ratio = config['terrain']['water_ratio']
        self.mountain_ratio = config['terrain']['mountain_ratio']
        
        # Drone
        self.start_x = config['drone']['start_x']
        self.start_y = config['drone']['start_y']
        self.start_z = config['drone'].get('start_z', 0)
        self.battery_capacity = config['drone']['battery_capacity']
        self.max_altitude = config['drone']['max_altitude']
        
        # Physics
        self.energy_base_cost = config['physics']['energy_base_cost']
        self.altitude_multiplier_enabled = config['physics']['altitude_multiplier']
        self.sensor_accuracy_decline = config['physics']['sensor_accuracy_decline']
        
        # Collision
        self.collision_detection = config['collision']['detection_enabled']
        self.tree_damage = config['collision']['tree_collision_damage']
        self.obstacle_damage = config['collision']['obstacle_collision_damage']

         # ===== COLLISION DETECTION =====
        self.collision_log = []
        self.last_collision = None
        
        # Observation
        self.observation_radius = config['observation']['radius']
        self.include_health = config['observation']['include_health']

        # quality of scaning
        self.min_good_altitude = config['observation'].get('min_good_altitude', 2.0)
        self.max_good_altitude = config['observation'].get('max_good_altitude', 10.0)
        self.min_scan_quality = config['observation'].get('min_scan_quality', 50.0)
        
        # episode
        self.max_steps = config['episode']['max_steps']
        self.seed = config['episode']['seed']
        
        np.random.seed(self.seed)
        
        self.world_map = self._generate_map()
        self.drone_knowledge = np.zeros((self.height, self.width))
    
        self.drone_x = self.start_x
        self.drone_y = self.start_y
        self.drone_z = self.start_z
        self.visited_cells = {(self.drone_x, self.drone_y)}
        
        self.step_count = 0
        
        self.collision_log = []
    
    #Generate map
    
    def _generate_map(self) -> np.ndarray:
        terrain = np.full((self.height, self.width), Terrain.FREE.value)
        
        num_obstacles = int(self.width * self.height * self.obstacle_ratio)
        for _ in range(num_obstacles):
            x = np.random.randint(0, self.width)
            y = np.random.randint(0, self.height)
            terrain[y, x] = Terrain.OBSTACLE.value
        
        # tree
        num_trees = int(self.width * self.height * self.tree_ratio)
        for _ in range(num_trees):
            x = np.random.randint(0, self.width)
            y = np.random.randint(0, self.height)
            terrain[y, x] = Terrain.TREE.value
        
        # water
        num_water = int(self.width * self.height * self.water_ratio)
        for _ in range(num_water):
            x = np.random.randint(0, self.width)
            y = np.random.randint(0, self.height)
            terrain[y, x] = Terrain.WATER.value
        
        # mountains
        num_mountains = int(self.width * self.height * self.mountain_ratio)
        for _ in range(num_mountains):
            x = np.random.randint(0, self.width)
            y = np.random.randint(0, self.height)
            terrain[y, x] = Terrain.MOUNTAIN.value

        for hy in range(max(0, self.start_y - 1), min(self.height, self.start_y + 2)):
            for hx in range(max(0, self.start_x - 1), min(self.width, self.start_x + 2)):
                terrain[hy, hx] = Terrain.FREE.value

        return terrain
    
    # simulation
    
    def step(self, action: Dict) -> Tuple[Dict, float, bool]:
        
        self.step_count += 1
        
        # calculate energy cost
        energy_cost = self._calculate_energy_cost(action)
        
        dx, dy, dz = action['move']
        new_x = self.drone_x + dx
        new_y = self.drone_y + dy
        new_z = self.drone_z + dz
        
        # check boarders
        if not (0 <= new_x < self.width and 0 <= new_y < self.height):
            reward = -50
            done = True
            observation = self._get_observation()
            return observation, reward, done
        
        # check altitude
        if not (0 <= new_z <= self.max_altitude):
            reward = -50
            done = True
            observation = self._get_observation()
            return observation, reward, done

        # check colission
        if self.detect_collision(new_x, new_y, new_z):

            terrain = self.classify_terrain(new_x, new_y)
            damage = self.calculate_collision_damage(terrain, self.drone_z)
            
            self.report_collision(terrain, damage, new_x, new_y, new_z)
            
            observation = self.get_observation()
            observation['collision'] = {
                'occurred': True,
                'terrain_type': terrain,
                'damage': damage
            }
            
            return observation, -50 * damage, True
        
        # Update position
        self.drone_x = new_x
        self.drone_y = new_y
        self.drone_z = new_z
        self.visited_cells.add((int(self.drone_x), int(self.drone_y)))
        
        # calculate reward
        exploration_ratio = len(self.visited_cells) / (self.width * self.height)
        
        reward = (
            exploration_ratio * 100 +        
            (50 if self._is_home() else 0) + 
            - energy_cost * 2 -               
            - self.step_count * 0.1          
        )
        
        # condition of end
        done = (self.step_count >= self.max_steps or 
                exploration_ratio > 0.8 or
                not self._is_drone_flyable())
        
        observation = self.get_observation()
        observation['collision'] = {'occurred': False}
        
        return observation, reward, done
    
    def _calculate_energy_cost(self, action: Dict) -> float:
        dx, dy, dz = action['move']
        
        # Basic cost of move
        distance = abs(dx) + abs(dy)
        cost = distance * self.energy_base_cost
        
        # cost of altitude
        if self.altitude_multiplier_enabled:
            altitude_multiplier = 1 + (self.drone_z / 10) ** 2
            cost *= altitude_multiplier
        
        # coast of change altitude
        cost += abs(dz) * 0.5
        
        return cost
    
    def _get_observation(self) -> Dict:
        return self.get_observation()

    def get_observation(self) -> Dict:
        
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
        local = np.full((2*self.observation_radius+1, 2*self.observation_radius+1), -1, dtype=float)
        
        for dy in range(-self.observation_radius, self.observation_radius+1):
            for dx in range(-self.observation_radius, self.observation_radius+1):
                y = int(self.drone_y) + dy
                x = int(self.drone_x) + dx
                
                if 0 <= x < self.width and 0 <= y < self.height:
                    local[dy+self.observation_radius, dx+self.observation_radius] = self.world_map[y, x]
                else:
                    local[dy+self.observation_radius, dx+self.observation_radius] = -1
        
        return local
    
    def calculate_scan_quality(self, altitude: float) -> float:
        if altitude < self.min_good_altitude:
            span = max(self.min_good_altitude, 1e-6)
            return max(0.0, min(100.0, (altitude / span) * 100.0))

        if altitude > self.max_good_altitude:
            span = max(self.max_altitude - self.max_good_altitude, 1e-6)
            return max(0.0, 100.0 - (altitude - self.max_good_altitude) / span * 100.0)

        return 100.0

    def is_scan_good(self, altitude: float) -> bool:
        return self.calculate_scan_quality(altitude) >= self.min_scan_quality

    def _get_health_info(self) -> Dict:
        return {}
    
    def _is_home(self) -> bool:
        return (self.drone_x == self.start_x and 
                self.drone_y == self.start_y)
    
    def _is_drone_flyable(self) -> bool:
        return True  # Буде заповнено з drone.health_monitor
    
    def reset(self) -> Dict:
        self.drone_x = self.start_x
        self.drone_y = self.start_y
        self.drone_z = self.start_z
        self.visited_cells = {(self.drone_x, self.drone_y)}
        self.step_count = 0
        self.collision_log = []
        
        return self._get_observation()

    def detect_collision(self, x: float, y: float, z: float) -> bool:
        # check boarders
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return True 
        
        #check altitude
        if z < 0 or z > self.max_altitude:
            return True
        
        if z <= 1:
            cell = int(self.world_map[int(y), int(x)])
            
            if cell == Terrain.OBSTACLE.value:
                return True  
            if cell == Terrain.WATER.value:
                return True 
            if cell == Terrain.MOUNTAIN.value:
                return True 
            if cell == Terrain.TREE.value:
                return True
        
        elif z > 1:
            cell = int(self.world_map[int(y), int(x)])
            
            if cell == Terrain.TREE.value:
                return np.random.random() < 0.3
            elif cell == Terrain.MOUNTAIN.value:
                return True 
            return False
        
        return False

    def classify_terrain(self, x: float, y: float) -> str:
        
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
        # Basic damage
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
        
        if altitude <= 1:
            altitude_factor = 1.5  # 150%
        elif altitude <= 3:
            altitude_factor = 1.2  # 120%
        elif altitude <= 5:
            altitude_factor = 0.8  # 80%
        else:
            altitude_factor = 0.2  # minimum in hight
        
        total_damage = base_damage * altitude_factor
        return min(1.0, total_damage)
    
    def get_danger_zones_around(self, x: float, y: float, radius: int = 3) -> list:
        
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
        
        collision_event = {
            'position': (x, y, z),
            'terrain_type': terrain_type,
            'damage': damage,
            'timestamp': len(self.collision_log)
        }
        
        self.last_collision = collision_event
        self.collision_log.append(collision_event)
        
        return collision_event