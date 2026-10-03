"""
Симулятор - запуск епізоду
"""

import numpy as np
from typing import Dict
from environment import DroneEnvironment
from drone import Drone, Battery, Motors, Sensors, Structure, HealthMonitor
from agents import AdaptiveHeightAgent


class Simulator:
    """
    Симулятор: запускає один епізод політу
    """
    
    def __init__(self, config: Dict, agent: AdaptiveHeightAgent):
        self.config = config
        self.agent = agent
        
        # Створити environment
        self.env = DroneEnvironment(config)
        
        # ===== ВСТАНОВИТИ СТАРТОВУ ПОЗИЦІЮ =====
        self.env.start_x = config['drone']['start_x']
        self.env.start_y = config['drone']['start_y']
        
        print(f"   📍 Стартова позиція в Environment: ({self.env.start_x}, {self.env.start_y})")
        
        # Створити дрона
        self.drone = self._create_drone(config)
        
        # Стан
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
    
    def _create_drone(self, config: Dict) -> Drone:
        """Створити дрона"""
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
        
        print(f"   🚁 Дрон створений на позиції: {drone.position}")
        
        return drone
    
    def run_episode(self) -> Dict:
        """Запустити один епізод"""
        
        print(f"\n🚁 ПОЧАТОК ПОЛІТУ")
        print("=" * 70)
        
        self.drone.take_off()
        
        self.drone.reset()
        observation = self._get_observation()
        done = False
        
        print(f"📍 Дрон стартує: {self.drone.position}")
        print(f"📍 Стартова позиція (home): ({self.env.start_x}, {self.env.start_y})")
        print(f"🎯 Макс кроків: {self.config['episode']['max_steps']}\n")
        
        iteration = 0
        while not done and self.step_count < self.config['episode']['max_steps']:
            iteration += 1
            
            # ===== ОТРИМАТИ СПОСТЕРЕЖЕННЯ =====
            observation = self._get_observation()
            
            # ===== АГЕНТ РОЗПІЗНУЄ =====
            try:
                action = self.agent.decide(observation)
            except Exception as e:
                print(f"❌ ПОМИЛКА В АГЕНТІ: {e}")
                raise
            
            # ===== ВИКОНАТИ ДІЮ =====
            target_altitude = action.get('altitude', 5.0)
            dx, dy, dz = action['move']

            new_x = self.drone.position[0] + dx
            new_y = self.drone.position[1] + dy
            new_z = self.drone.position[2]  # Z буде змінено в move()

            # ===== ПЕРЕВІРИТИ ГРАНИЦІ =====
            if not (0 <= new_x < self.env.width and 0 <= new_y < self.env.height):
                # Удар в границу карты
                collision_detected = True
                terrain = "wall"
                damage = 1.0
                
                print(f"\nКрок {iteration}: 🧱 УДАР В СТІНУ! Позиція ({new_x}, {new_y})")
            else:
                # ===== ПЕРЕВІРИТИ КОЛІЗІЮ =====
                collision_detected = self.env.detect_collision(new_x, new_y, 
                                                            self.drone.position[2])
                if collision_detected:
                    terrain = self.env.classify_terrain(new_x, new_y)
                    damage = self.env.calculate_collision_damage(terrain, 
                                                                self.drone.position[2])
                    
                    if iteration <= 20:
                        print(f"\nКрок {iteration}: 💥 ЗІТКНЕННЯ з {terrain}!")

            if collision_detected:
                self.env.report_collision(terrain if collision_detected else "free", 
                                        damage if collision_detected else 0, 
                                        new_x, new_y, 
                                        self.drone.position[2])
                self.drone.record_collision(terrain if collision_detected else "free", 
                                        damage if collision_detected else 0)
                
                # Оновити здоров'я
                self.drone.update_health(
                    energy_consumed=1.0,
                    motor_stress=[0.3, 0.3, 0.3, 0.3],
                    altitude=self.drone.get_altitude(),
                    collision_occurred=True,
                    collision_damage=damage if collision_detected else 0
                )
                
            else:
                # Переміститись...
                move_result = self.drone.move(dx, dy, dz, target_altitude=target_altitude)
                
                if move_result:
                    # Оновити позицію у environment
                    self.env.drone_x = self.drone.position[0]
                    self.env.drone_y = self.drone.position[1]
                    self.env.drone_z = self.drone.position[2]
                    self.env.visited_cells.add((int(self.drone.position[0]), 
                                            int(self.drone.position[1])))
                    
                    # Оновити здоров'я
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
                    
                    print(f"Крок {iteration}: Позиція {self.drone.position}, "
                        f"Висота {self.drone.position[2]:.1f}м, "
                        f"Батарея {observation['health']['battery']['charge_percent']:.1f}%")
                else:
                    done = True
                    if iteration <= 20:
                        print(f"\nКрок {iteration}: ❌ Дрон не може летіти!")
            
            # ===== ПЕРЕВІРИТИ УМОВИ ЗАВЕРШЕННЯ =====
            if not done:
                done = self._check_termination_conditions(observation)
        
        print("\n" + "=" * 70)
        print("🏁 ПОЛІТ ЗАВЕРШЕНО\n")
        
        self.drone.land()
        
        return self._calculate_episode_result()
    
    def _get_observation(self) -> Dict:
        """Отримати спостереження"""
        
        local_map = self.env.get_local_map()
        
        motors_list = [
            {
                'efficiency': m['efficiency'],
                'temperature': m['temperature'],
                'wear': m['wear'],
                'status': m['status']
            }
            for m in self.drone.motors.motors
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
            
            # ❌ НЕ передаємо map_width/map_height/start_x/start_y!
            
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
        """Розрахувати енергію за крок"""
        dx, dy, dz = action['move']
        distance = abs(dx) + abs(dy)
        
        cost = distance * self.env.energy_base_cost
        
        altitude_multiplier = 1 + (self.drone.position[2] / 10) ** 2
        cost *= altitude_multiplier
        
        cost += abs(dz) * 0.5
        
        energy_percent = (cost / self.env.battery_capacity) * 100
        self.drone.battery.discharge(energy_percent)
        
        return energy_percent
    
    def _calculate_motor_stress(self, action: Dict) -> list:
        """Розрахувати стрес на мотори"""
        return [0.3, 0.3, 0.3, 0.3]
    
    def _calculate_reward(self) -> float:
        """Розрахувати нагороду за крок"""
        exploration = len(self.env.visited_cells) / (self.env.width * self.env.height)
        return exploration * 10 - self.step_count * 0.1
    
    def _check_termination_conditions(self, observation: Dict) -> bool:
        """Перевірити умови завершення"""
        
        health = observation['health']
        battery = health['battery']['charge_percent']
        position = observation['position']
        exploration = observation['exploration_ratio']
        
        # ===== УМОВА 1: ДОМ =====
        # ⚠️ ВАЖЛИВО: Перевіряємо ТОЧНЕ місцезнаходження
        is_at_home = (
            abs(position[0] - self.env.start_x) < 0.5 and
            abs(position[1] - self.env.start_y) < 0.5
        )
        
        
        # ===== УМОВА 2: БАТАРЕЯ КРИТИЧНА =====
        if battery < 10:
            print(f"   🔴 Батарея критична ({battery:.1f}%)!")
            return True
        
        # ===== УМОВА 3: ДРОН ПОЛАМАНИЙ =====
        if not health['structure']['is_flightworthy']:
            print(f"   💥 Дрон не придатний до польоту!")
            return True
        
        # ===== УМОВА 4: ДОСЛІДЖЕНО ДОСТАТНЬО =====
        if exploration > 0.8:
            print(f"   🎉 Досліджено {exploration*100:.1f}%!")
            return True
        
        return False
    
    def _record_step_data(self):
        """Записати дані кроку"""
        self.episode_data['steps'].append(self.step_count)
        self.episode_data['positions'].append(self.drone.position)
        self.episode_data['energy'].append(self.drone.battery.get_remaining_range())
        self.episode_data['health'].append(
            self.drone.health_monitor.get_overall_health()
        )
    
    def _calculate_episode_result(self) -> Dict:
        """Розрахувати фінальні результати"""
        
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
            'episode_data': self.episode_data
        }
        
        return result