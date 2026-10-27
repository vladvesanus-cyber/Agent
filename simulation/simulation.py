import numpy as np
from typing import Dict
from environment import DroneEnvironment
from drone import Drone, Battery, Motors, Sensors, Structure, HealthMonitor
from agents import AdaptiveHeightAgent


class Simulator:
    
    def __init__(self, config: Dict, agent: AdaptiveHeightAgent):
        self.config = config
        self.agent = agent
        
        # create environment
        self.env = DroneEnvironment(config)
        
        # create stat point
        self.env.start_x = config['drone']['start_x']
        self.env.start_y = config['drone']['start_y']
        
        #create drone
        self.drone = self._create_drone(config)
        
        # stan
        self.episode_data = {
            'steps': [],
            'positions': [],
            'rewards': [],
            'energy': [],
            'health': [],
            'collision_events': []
        }
        
        self.step_count = 0
        self.total_reward = 0

        
        self.mission_success = False
        self.bad_scan_count = 0  # count of bad scans

        self.success_exploration_threshold = config.get('episode', {}).get(
            'success_exploration_threshold', 0.6
        )
    
    def _create_drone(self, config: Dict) -> Drone:
        battery = Battery(capacity=config['drone']['battery_capacity'])
        motors = Motors(num_motors=4)
        sensors = Sensors(num_sensors=3)
        structure = Structure(num_propellers=4)
        health_monitor = HealthMonitor(battery, motors, sensors, structure)
        
        drone = Drone(
            battery=battery,
            motors=motors,
            sensors=sensors,
            structure=structure,
            health_monitor=health_monitor,
            position=(config['drone']['start_x'], 
                     config['drone']['start_y'],
                     config['drone'].get('start_z', 0))
        )
        
        return drone
    
    def run_episode(self) -> Dict:
        self.drone.take_off()
        
        self.drone.reset()
        observation = self._get_observation()
        done = False
        iteration = 0
        while not done and self.step_count < self.config['episode']['max_steps']:
            iteration += 1
            
            # get observation
            observation = self._get_observation()
            
            try:
                action = self.agent.decide(observation)
            except Exception as e:
                print(f"❌ ПОМИЛКА В АГЕНТІ: {e}")
                raise
            
            # act
            target_altitude = action.get('altitude', 5.0)
            dx, dy, dz = action['move']

            new_x = self.drone.position[0] + dx
            new_y = self.drone.position[1] + dy
            new_z = self.drone.position[2] 

            # check boarders
            if not (0 <= new_x < self.env.width and 0 <= new_y < self.env.height):
                # collision 
                collision_detected = True
                terrain = "wall"
                damage = 1.0
                
            else:
                collision_detected = self.env.detect_collision(new_x, new_y, 
                                                            self.drone.position[2])
                if collision_detected:
                    terrain = self.env.classify_terrain(new_x, new_y)
                    damage = self.env.calculate_collision_damage(terrain, 
                                                                self.drone.position[2])

            if collision_detected:
                self.env.report_collision(terrain, damage, new_x, new_y,
                                        self.drone.position[2])
                self.drone.record_collision(terrain, damage)

                energy_consumed = self._calculate_energy_consumed(action)
                motor_stress = self._calculate_motor_stress(action)

                self.drone.update_health(
                    energy_consumed=energy_consumed,
                    motor_stress=motor_stress,
                    altitude=self.drone.get_altitude(),
                    collision_occurred=True,
                    collision_damage=damage,
                )

            else:
                # move
                move_result = self.drone.move(dx, dy, dz, target_altitude=target_altitude)
                
                if move_result:
                    # update position 
                    self.env.drone_x = self.drone.position[0]
                    self.env.drone_y = self.drone.position[1]
                    self.env.drone_z = self.drone.position[2]

                    scan_quality = self.env.calculate_scan_quality(self.drone.position[2])
                    scan_ok = scan_quality >= self.env.min_scan_quality

                    if scan_ok:
                        self.env.visited_cells.add((int(self.drone.position[0]),
                                                int(self.drone.position[1])))
                    else:
                        self.bad_scan_count += 1

                    # update health
                    energy_consumed = self._calculate_energy_consumed(action)
                    motor_stress = self._calculate_motor_stress(action)
                    
                    self.drone.update_health(
                        energy_consumed=energy_consumed,
                        motor_stress=motor_stress,
                        altitude=self.drone.get_altitude(),
                        collision_occurred=False,
                        collision_damage=0
                    )
                    
                    reward = self._calculate_reward()
                    self.total_reward += reward
                    
                    self._record_step_data()
                    self.step_count += 1
                    
                else:
                    done = True
            
            # check end condition
            if not done:
                done = self._check_termination_conditions(observation)
        
        self.drone.land()
        
        return self._calculate_episode_result()
    
    def _get_observation(self) -> Dict:
        
        local_map = self.env.get_local_map()
        
        motors_list = [
            {
                "efficiency": motor["efficiency"],
                "temperature": motor["temperature"],
                "wear": motor["wear"],
                "rpm": motor["rpm"],
                "status": motor["status"],
            }
            for motor in self.drone.motors.motors
        ]
        
        sensors_list = [
            {
                'type': s['type'],
                'accuracy': s['accuracy'],
                'dirt_level': s['dirt_level'],
                'status': s['status']
            }
            for s in self.drone.sensors.sensors
        ]
        
        structure_integrity = self.drone.structure.get_structural_integrity()
        is_flightworthy = self.drone.structure.is_flightworthy()
        
        overall_health = self.drone.health_monitor.get_overall_health()
        critical_alerts = self.drone.health_monitor.get_critical_alerts()
        
        visited_cells_set = self.env.visited_cells
        visited_cells_count = len(visited_cells_set)
        
        observation = {
            'position': tuple(self.drone.position),
            'local_map': local_map,  # ← Локальна карта!
            'exploration_ratio': visited_cells_count / (self.env.width * self.env.height),
            'visited_cells': visited_cells_set,
            'visited_cells_count': visited_cells_count,
            'step_count': self.step_count,

            'scan_quality': self.env.calculate_scan_quality(self.drone.position[2]),
            'scan_ok': self.env.is_scan_good(self.drone.position[2]),

            'home_position': (self.env.start_x, self.env.start_y),  # ← Для повернення додому!
            
            'health': {
                'overall_health': overall_health,
                'is_healthy': self.drone.health_monitor.is_system_healthy(),
                'critical_alerts': critical_alerts,
                
                'battery': {
                    'charge_percent': self.drone.battery.get_remaining_range(),
                    'temperature': self.drone.battery.temperature,
                    'health': self.drone.battery.health,
                    'is_healthy': self.drone.battery.is_healthy(),
                    'cycles': self.drone.battery.charge_cycles
                },
                
                'motors': motors_list,
                'sensors': sensors_list,
                
                'structure': {
                    'integrity': structure_integrity,
                    'is_flightworthy': is_flightworthy,
                    'crash_count': self.drone.structure.crash_count,
                    'propeller_health': self.drone.structure.propeller_health
                }
            }
        }
        
        return observation
    
    def _calculate_energy_consumed(self, action: Dict) -> float:
        dx, dy, dz = action['move']
        distance = abs(dx) + abs(dy)
        
        cost = distance * self.env.energy_base_cost
        
        altitude_multiplier = 1 + (self.drone.position[2] / 20) ** 2
        cost *= altitude_multiplier
        
        cost += abs(dz) * 0.3
        
        energy_percent = (cost / self.env.battery_capacity) * 100
        
        return energy_percent
    
    def _calculate_motor_stress(self, action: Dict) -> list:
        """Calculate motor load from horizontal and vertical movement."""

        dx, dy, dz = action["move"]

        horizontal = min(
            1.0,
            (abs(dx) + abs(dy)) / 2.0,
        )

        vertical = min(
            1.0,
            abs(dz) / 2.0,
        )

        altitude_load = min(
            1.0,
            self.drone.position[2] / self.env.max_altitude,
        )

        stress = min(
            1.0,
            0.15
            + 0.55 * horizontal
            + 0.25 * vertical
            + 0.15 * altitude_load,
        )

        return [
            stress
            for _ in self.drone.motors.motors
        ]
        
    def _calculate_reward(self) -> float:
        exploration = len(self.env.visited_cells) / (self.env.width * self.env.height)
        return exploration * 10 - self.step_count * 0.1
    
    def _check_termination_conditions(self, observation: Dict) -> bool:
        
        health = observation['health']
        battery = health['battery']['charge_percent']
        position = observation['position']
        exploration = observation['exploration_ratio']
        
        #1 Recharge
        is_at_home = (
            abs(position[0] - self.env.start_x) < 0.5 and
            abs(position[1] - self.env.start_y) < 0.5
        )
        
        if is_at_home and battery < 95:
            self.drone.recharge_battery(100.0 - battery)
            battery = 100
            # Go on
        
        # battery is critical
        if battery < 10:
            return True
        
        # Drone cant fly
        if not health['structure']['is_flightworthy']:
            return True
        
        if exploration > self.success_exploration_threshold and is_at_home:
            self.mission_success = True
            return True

        return False
    
    def _record_step_data(self):
        """write step data"""
        self.episode_data['steps'].append(self.step_count)
        self.episode_data['positions'].append(self.drone.position)
        self.episode_data['energy'].append(self.drone.battery.get_remaining_range())
        self.episode_data['health'].append(
            self.drone.health_monitor.get_overall_health()
        )
    
    def _calculate_episode_result(self) -> Dict:
        
        observation = self._get_observation()
        
        result = {
            'total_steps': self.step_count,
            'total_reward': self.total_reward,
            'exploration_ratio': observation['exploration_ratio'],
            'explored_cells': observation['visited_cells'],
            'final_battery': observation['health']['battery']['charge_percent'],
            'final_health': observation['health']['overall_health'],
            'final_position': observation['position'],
            'collision_count': self.drone.structure.crash_count,
            'mission_success': self.mission_success,
            'bad_scan_count': self.bad_scan_count,
            'episode_data': self.episode_data
        }
        
        return result