"""
ExperimentRunner - запускає декілька симуляцій з різними seeds
"""

from typing import Dict, List
from agents import AdaptiveHeightAgent
from utils import ConfigLoader
from .simulation import Simulator


class ExperimentRunner:
    """
    Запускає експерименти:
    - 3 конфігурації (easy, medium, hard)
    - 20 запусків кожної (різні seeds)
    - Збирає статистику
    """
    
    def __init__(self):
        self.config_loader = ConfigLoader()
        self.results = {}
    
    def run_full_experiment(self) -> Dict:
        """
        Запустити ВСІ експерименти
        3 конфіги × 20 seeds = 60 симуляцій
        """
        
        experiments_config = self.config_loader.load_experiments_config()
        
        for experiment in experiments_config['experiments']:
            config_name = experiment['config']
            runs = experiment['runs']
            seeds = experiment['seeds']
            
            print(f"\n{'='*70}")
            print(f"🚀 ЕКСПЕРИМЕНТ: {experiment['name']}")
            print(f"   Конфіг: {config_name}")
            print(f"   Запусків: {runs}")
            print(f"{'='*70}\n")
            
            results = self._run_configuration(config_name, seeds)
            self.results[config_name] = results
        
        return self.results
    
    def _run_configuration(self, config_name: str, seeds: List[int]) -> List[Dict]:
        """
        Запустити конфіг N разів з різними seeds
        """
        
        config = self.config_loader.get_config(config_name)
        results = []
        
        for i, seed in enumerate(seeds):
            print(f"  Запуск {i+1}/{len(seeds)} (seed={seed})...", end=" ")
            
            # Встановити seed
            config['episode']['seed'] = seed
            
            # Створити агента
            agent = AdaptiveHeightAgent()
            
            # Запустити симуляцію
            simulator = Simulator(config, agent)
            result = simulator.run_episode()
            
            results.append(result)
            
            print(f"✅ Експлорація: {result['exploration_ratio']*100:.1f}%")
        
        return results