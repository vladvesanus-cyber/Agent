"""
Simulator - запуск епізодів БЕЗ метрик
Метрики додаються потім в тестах
"""

import numpy as np
from typing import Dict, Tuple
from environment import DroneEnvironment, Terrain
from drone import Drone, Battery, Motors, Sensors, Structure, HealthMonitor
from agents import AdaptiveHeightAgent


class Simulator:
    """
    Симулятор: запускає один епізод
    Тільки логує дані, не розраховує метрики
    """
    
    def __init__(self, config: Dict, agent: AdaptiveHeightAgent):
        """
        Args:
            config: Конфігурація
            agent: Агент
        """
        
        self.config = config
        self.agent = agent
        
        # Створити environment
        self.env = DroneEnvironment(config)
        
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
        
        return drone
    
    def run_episode(self) -> Dict:
        """
        Запустити один епізод
        Повертає СИРІ дані, без обробки
        """
        
        observation = self.env.reset()
        self.drone.reset()
        done = False
        
        while not done:
            # Агент розпізнує
            action = self.agent.decide(observation)
            
            # Крок в environment
            observation, reward, done = self.env.step(action)
            self.total_reward += reward
            
            # Оновити здоров'я дрона
            energy_consumed = self._calculate_energy_consumed(action)
            motor_stress = self._calculate_motor_stress(action)
            
            self.drone.health_monitor.update(
                energy_consumed=energy_consumed,
                motor_stress=motor_stress,
                altitude=self.drone.position[2],
                collision_occurred=observation.get('collision', {}).get('occurred', False),
                collision_damage=observation.get('collision', {}).get('damage', 0),
                ambient_temp=25
            )
            
            # Записати дані (СИРІ, без обробки)
            self._record_step_data(observation, action, reward)
            
            self.step_count += 1
        
        # Повернути сирі дані
        return {
            'total_steps': self.step_count,
            'total_reward': self.total_reward,
            'raw_data': self.episode_data,
            'final_position': self.drone.position,
            'exploration_ratio': len(self.env.visited_cells) / (self.env.width * self.env.height),
            'explored_cells': len(self.env.visited_cells)
        }
    
    def _calculate_energy_consumed(self, action: Dict) -> float:
        """Енергія за крок"""
        dx, dy, dz = action['move']
        distance = abs(dx) + abs(dy)
        
        cost = distance * self.env.energy_base_cost
        
        if True:  # altitude_multiplier_enabled
            altitude_multiplier = 1 + (self.drone.position[2] / 10) ** 2
            cost *= altitude_multiplier
        
        cost += abs(dz) * 0.5
        
        energy_percent = (cost / self.env.battery_capacity) * 100
        self.drone.battery.discharge(energy_percent)
        
        return energy_percent
    
    def _calculate_motor_stress(self, action: Dict) -> list:
        """Стрес на мотори"""
        return [0.3, 0.3, 0.3, 0.3]  # Спрощено
    
    def _record_step_data(self, observation: Dict, action: Dict, reward: float):
        """Записати сирі дані"""
        self.episode_data['steps'].append(self.step_count)
        self.episode_data['positions'].append(self.drone.position)
        self.episode_data['rewards'].append(reward)
        self.episode_data['energy'].append(
            observation['health']['battery']['charge_percent']
        )
        self.episode_data['health'].append(
            observation['health']['overall_health']
        )