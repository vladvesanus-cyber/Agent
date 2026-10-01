"""
Тести компонентів
"""

import pytest
from drone import Battery, Motors, Sensors, Structure
from environment import DroneEnvironment
from tests import Metrics, Statistics


class TestBattery:
    def test_discharge(self):
        battery = Battery(capacity=100)
        battery.discharge(10)
        assert battery.get_remaining_range() == 90
    
    def test_health_degradation(self):
        battery = Battery(capacity=100)
        battery.recharge()  # 1 цикл
        battery.update_health()
        assert battery.health < 100


class TestMetrics:
    def test_performance_calculation(self):
        result = {
            'exploration_ratio': 0.85,
            'total_steps': 200,
            'final_battery': 30,
            'returned_home': True
        }
        
        performance = Metrics.calculate_performance(result)
        assert performance > 0  # Позитивна нагорода
    
    def test_statistics(self):
        values = [10, 20, 30, 40, 50]
        
        assert Statistics.calculate_mean(values) == 30
        assert Statistics.calculate_min_max(values) == (10, 50)


class TestEnvironment:
    def test_collision_detection(self):
        config = {
            'map': {'width': 20, 'height': 20},
            'terrain': {'obstacle_ratio': 0.2, 'tree_ratio': 0.05, 
                       'water_ratio': 0.01, 'mountain_ratio': 0.01},
            'drone': {'start_x': 10, 'start_y': 10, 'battery_capacity': 100, 
                     'max_altitude': 20},
            'physics': {'energy_base_cost': 1.0, 'altitude_multiplier': True},
            'observation': {'radius': 2},
            'episode': {'max_steps': 1000, 'seed': 42}
        }
        
        env = DroneEnvironment(config)
        
        # Тест колізії з границею
        assert env.detect_collision(-1, 10, 5) == True
        assert env.detect_collision(10, 10, -1) == True
        assert env.detect_collision(10, 10, 25) == True