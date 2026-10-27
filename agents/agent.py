import heapq
import numpy as np
import random
from typing import Dict


class AdaptiveHeightAgent:
    
    def __init__(self, success_threshold: float = 0.6,
                 cool_on: float = 40.0, cool_off: float = 35.0):
        self.boundary_cells = set()  # Cells where dorne find boundary
        self.safe_directions = {}     # Directions without hits
        self.stuck_count = 0
        self.last_position = None

        # ---- memory built ONLY from percepts (local windows) ----
        self.known = {}               # (x, y) -> terrain code seen so far
        self.success_threshold = success_threshold
        self.cool_on = cool_on        # battery temp (C) where hovering starts
        self.cool_off = cool_off      # battery temp (C) where flying resumes
        self.cooling = False
        # ---- learned energy model (from observed battery drops) ----
        self.energy_per_step = 1.0    # EMA of battery units used per moving step
        self._last_battery = None
        self._last_was_move = False
    
    def decide(self, observation: Dict) -> Dict:
        """
        Modes:
        1. EXPLORATION (battery > 30%) - normal exploration
        2. RETURN HOME (battery < 30%) - aggressive flight to home
        """
        
        try:
            self._update_known_map(observation)
            situation = self._analyze_situation(observation)

            # --- thermal protection: hover (zero energy) until battery cools ---
            temp = situation['battery_temp']
            if temp >= self.cool_on:
                self.cooling = True
            elif temp <= self.cool_off:
                self.cooling = False
            x, y, z = observation['position']
            c = situation['local_map'].shape[0] // 2
            under_tree = int(situation['local_map'][c, c]) == 2
            if self.cooling and not under_tree:
                self.last_position = observation['position']
                self._last_was_move = False
                return {'move': (0, 0, 0), 'altitude': max(z, 2.0)}

            # learn how expensive one move is on this map/drone
            battery = situation['battery']
            if self._last_battery is not None and self._last_was_move:
                drop = self._last_battery - battery
                if 0 < drop < 20:
                    self.energy_per_step = 0.9 * self.energy_per_step + 0.1 * drop
            self._last_battery = battery

            # return home when remaining energy barely covers the way back
            # (distance * learned cost * safety factor + reserve) OR goal reached
            dist_home = (abs(x - observation['home_position'][0]) +
                         abs(y - observation['home_position'][1]))
            need = max(15.0, self.energy_per_step * dist_home * 1.4 + 12.0)
            home_mode = (battery < need or
                         observation['exploration_ratio'] > self.success_threshold)
            
            # decide altitude
            if home_mode:
                # for returning
                optimal_altitude = 2.0
            else:
                optimal_altitude = self._choose_altitude(situation)
            
            # Chose direction
            if home_mode:
                # Go home
                next_move = self._go_home_direction(observation, situation)
            else:
                next_move = self._choose_direction(observation, situation)
            
            self.last_position = observation['position']
            self._last_was_move = True

            return {
                'move': next_move,
                'altitude': optimal_altitude
            }
        
        except Exception as e:
            print(f"❌ ПОМИЛКА В АГЕНТІ: {e}")
            raise
    
    def _analyze_situation(self, observation: Dict) -> Dict:
        
        health = observation['health']
        position = observation['position']
        local_map = observation['local_map']
        
        # Battery
        battery = health['battery']['charge_percent']
        battery_temp = health['battery']['temperature']
        
        # Motors
        motors = health['motors']
        motor_health = np.mean([m['efficiency'] for m in motors])
        motor_temp = np.mean([m['temperature'] for m in motors])
        
        # Sensors
        sensors = health['sensors']
        sensor_accuracy = np.mean([s['accuracy'] for s in sensors])
        sensor_dirt = np.mean([s['dirt_level'] for s in sensors])
        
        # Structure
        structure = health['structure']
        integrity = structure['integrity']
        is_flightworthy = structure['is_flightworthy']
        
        # Health
        overall_health = health['overall_health']
        critical_alerts = health['critical_alerts']
        
        # analize
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
        -1 is boundary
        """
        
        has_water_below = False
        has_obstacles_around = False
        has_trees_around = False
        boundary_directions = []  # Directions to boundary cells
        
        center = local_map.shape[0] // 2
        
        # Analyze local map
        for dy in range(-center, center+1):
            for dx in range(-center, center+1):
                y = center + dy
                x = center + dx
                
                if 0 <= y < local_map.shape[0] and 0 <= x < local_map.shape[1]:
                    cell = local_map[y, x]
                    
                    # Check for boundary
                    if cell == -1:
                        if dx != 0 or dy != 0:  # Not the center cell
                            boundary_directions.append((dx, dy))
                        continue
                    
                    cell = int(cell)
                    
                    # Check for water below
                    if cell == 3 and dy == 0 and dx == 0:
                        has_water_below = True
                    
                    # Check for obstacles and trees around
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
        """Choose altitude"""
        
        local_obs = situation['local_obstacles']
        battery = situation['battery']
        sensor_dirt = situation['sensor_dirt']
        overall_health = situation['overall_health']
        
        # Critical condition
        if overall_health < 30 or not situation['is_flightworthy']:
            return 0.0
        
        # If has water
        if local_obs['has_water_below']:
            return 8.0  # Достатньо щоб уникнути води
        
        # state of sensors
        if sensor_dirt > 60:
            return 9.0
        elif sensor_dirt > 40:
            return 7.0
        
        # battery is critical low
        if battery < 15:
            return 1.0  # Мінімальна висота
        
        # battery is low
        if battery < 30:
            return 3.0  # Економна висота
        
        # tempreture of motors
        if situation['motor_temp'] > 60:
            return 10.0  # Cool down
        elif situation['motor_temp'] > 50:
            return 8.0
        
        if local_obs['has_trees_around']:
            return 6.5
        
        return 6.0
    
    def _choose_direction(self, observation: Dict, situation: Dict) -> tuple:
        
        position = observation['position']
        visited_cells = observation['visited_cells']
        local_obs = situation['local_obstacles']
        local_map = observation['local_map']
        
        if not isinstance(visited_cells, set):
            visited_cells = set()
        
        # Critical situation
        if situation['overall_health'] < 20 or situation['battery'] < 5:
            return self._go_away_direction(position)
        
        # all directions
        directions = [
            (1, 0, 0),    # Right
            (-1, 0, 0),   # Left
            (0, 1, 0),    # Down
            (0, -1, 0),   # Up
        ]
        
        center = local_map.shape[0] // 2
        altitude = situation['current_altitude']
        
        # category of directions
        safe_new = []         
        safe_old = []        
        risky_new = []        
        risky_old = []        
        
        for dx, dy, dz in directions:
            local_x = center + dx
            local_y = center + dy
            
            if 0 <= local_x < local_map.shape[1] and 0 <= local_y < local_map.shape[0]:
                cell_value = local_map[local_y, local_x]
                
                # boundary
                if cell_value == -1:
                    continue
                
                cell_int = int(cell_value)
                
                is_safe = False
                if cell_int == 0:  # FREE
                    is_safe = True
                elif cell_int == 1 and altitude > 1:  # OBSTACLE вище 1м
                    is_safe = True
                elif cell_int == 3 and altitude > 1:  # WATER вище 1м
                    is_safe = True
                
                # decide if cell is new
                new_x = position[0] + dx
                new_y = position[1] + dy
                cell_coord = (int(new_x), int(new_y))
                is_new = cell_coord not in visited_cells
                
                # divide in category
                if is_safe:
                    if is_new:
                        safe_new.append((dx, dy, dz))
                    else:
                        safe_old.append((dx, dy, dz))
                else:
                    if cell_int == 2 and altitude >= 2:
                        if is_new:
                            risky_new.append((dx, dy, dz))
                        else:
                            risky_old.append((dx, dy, dz))
        
        if safe_new:
            best_direction = random.choice(safe_new)
            return best_direction
        
        frontier_move = self._move_toward_exploration_frontier(
            position,
            visited_cells
        )

        if frontier_move is not None:
            return frontier_move

        if safe_old:
            best_direction = random.choice(safe_old)
            return best_direction

        if risky_new:
            best_direction = random.choice(risky_new)
            return best_direction
        
        if risky_old:
            best_direction = random.choice(risky_old)
            return best_direction
        
        return self._go_away_from_boundary(local_map)
    
    @staticmethod
    def _go_away_from_boundary(local_map: np.ndarray) -> tuple:
        
        center = local_map.shape[0] // 2
        
        # find direction withou boundary
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
            return (0, 0, 1)
    
    def _go_away_direction(self, position: tuple) -> tuple:
        
        directions = [
            (1, 0, 0),
            (-1, 0, 0),
            (0, 1, 0),
            (0, -1, 0),
        ]
        
        return random.choice(directions)
    
    def _go_home_direction(self, observation: Dict, situation: Dict) -> tuple:
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

        planned = self._plan_step(position, lambda c: c == (home_x, home_y), altitude)
        if planned is not None:
            return planned

        safe_candidates = []  # (new distance to home, direction)

        for dx, dy, dz in directions:
            local_x = center + dx
            local_y = center + dy

            if not (0 <= local_x < local_map.shape[1] and 0 <= local_y < local_map.shape[0]):
                continue

            cell_value = local_map[local_y, local_x]
            if cell_value == -1:  # boundary of map
                continue

            cell_int = int(cell_value)

            if cell_int == 0:
                is_safe = True
            elif cell_int == 4:
                is_safe = False
            elif altitude > 1:
                is_safe = True
            else:
                is_safe = False

            if not is_safe:
                continue

            new_distance = abs((x + dx) - home_x) + abs((y + dy) - home_y)
            safe_candidates.append((new_distance, (dx, dy, dz)))

        if safe_candidates:
            # choose best home direction
            safe_candidates.sort(key=lambda c: c[0])
            return safe_candidates[0][1]

        # choose even danger direction
        for dx, dy, dz in directions:
            local_x = center + dx
            local_y = center + dy
            if (0 <= local_x < local_map.shape[1] and 0 <= local_y < local_map.shape[0]
                    and local_map[local_y, local_x] != -1):
                return (dx, dy, dz)

        # or increse altitude
        return (0, 0, 1)

    # ------------------------------------------------------------------
    # memory + path planning on the map the agent has SEEN (no env access)
    # ------------------------------------------------------------------
    def _update_known_map(self, observation: Dict):
        lm = observation['local_map']
        x0, y0 = int(observation['position'][0]), int(observation['position'][1])
        r = lm.shape[0] // 2
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                v = lm[dy + r, dx + r]
                if v != -1:
                    self.known[(x0 + dx, y0 + dy)] = int(v)

    def _cell_cost(self, cell, altitude):
        """Cost of entering a known cell, None if impassable."""
        t = self.known.get(cell)
        if t is None or t == 4:            # unknown or mountain
            return None
        if t == 0:
            return 1
        if altitude <= 1:                  # obstacle/water/tree block at low altitude
            return None
        return 5 if t == 2 else 1          # tree = 30 % crash risk -> expensive

    def _plan_step(self, position, is_goal, altitude):
        """Dijkstra over known cells; returns first step (dx, dy, 0) or None."""
        start = (int(position[0]), int(position[1]))
        alt = max(altitude, 2.0)           # we always fly >= 2 m when moving on
        pq = [(0, start, None)]
        best = {start: 0}
        while pq:
            d, cell, first = heapq.heappop(pq)
            if d > best.get(cell, 1e9):
                continue
            if cell != start and is_goal(cell):
                return first
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (cell[0] + dx, cell[1] + dy)
                c = self._cell_cost(nxt, alt)
                if c is None:
                    continue
                nd = d + c
                if nd < best.get(nxt, 1e9):
                    best[nxt] = nd
                    heapq.heappush(pq, (nd, nxt, first or (dx, dy, 0)))
        return None

    def _move_toward_exploration_frontier(
        self,
        position: tuple,
        visited_cells: set
    ):
        """Shortest known path from the CURRENT position to the nearest
        known-but-unvisited cell."""
        return self._plan_step(
            position,
            lambda c: c in self.known and c not in visited_cells,
            position[2],
        )
