"""
Завантажувати конфіги з YAML файлів
"""

import yaml
from pathlib import Path
from typing import Dict


class ConfigLoader:
    """Завантажувач конфігурацій"""
    
    def __init__(self, config_dir: str = 'config'):
        self.config_dir = Path(config_dir)
    
    def load_environment_config(self) -> Dict:
        """Завантажити базову конфігурацію environment"""
        path = self.config_dir / 'environment.yaml'
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    def load_experiments_config(self) -> Dict:
        """Завантажити конфігурації експериментів"""
        path = self.config_dir / 'experiments.yaml'
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    def get_config(self, config_name: str) -> Dict:
        """
        Отримати конфіг для конкретної конфігурації
        
        Args:
            config_name: 'easy', 'medium', або 'hard'
        
        Returns:
            Об'єднана конфігурація (базова + конкретна)
        """
        base = self.load_environment_config()
        experiments = self.load_experiments_config()
        
        config_dict = experiments['configs'][config_name]
        
        # Об'єднуємо базові параметри з конкретними
        merged = self._merge_configs(base, config_dict)
        
        return merged
    
    def _merge_configs(self, base: Dict, specific: Dict) -> Dict:
        """Об'єднати два конфіги (specific перевизначає base)"""
        merged = base.copy()
        
        for key, value in specific.items():
            if isinstance(value, dict) and key in merged:
                merged[key].update(value)
            else:
                merged[key] = value
        
        return merged