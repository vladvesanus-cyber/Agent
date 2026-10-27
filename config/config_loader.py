import copy
import yaml
from pathlib import Path
from typing import Dict, List
import os

class ConfigLoader:
    
    def __init__(self, config_dir: str = 'config'):
        
        if os.path.isabs(config_dir):
            self.config_dir = config_dir
        else:
            self.config_dir = os.path.join(os.getcwd(), config_dir)
        
        self.config_dir = os.path.abspath(self.config_dir)
        
        
        if not os.path.isdir(self.config_dir):
            
            raise FileNotFoundError(
                f"❌ Config directory not found: {self.config_dir}\n"
                f"   Make sure it exists!"
            )
        
        
        env_file = os.path.join(self.config_dir, 'environment.yaml')
        exp_file = os.path.join(self.config_dir, 'experiments.yaml')
        
        
        if not os.path.exists(env_file) or not os.path.exists(exp_file):
            raise FileNotFoundError(
                f"❌ Config files not found\n"
                f"   Required files:\n"
                f"   - {env_file}\n"
                f"   - {exp_file}"
            )
        
        
        try:
            self.base_config = self._load_yaml('environment.yaml')
            self.experiments_config = self._load_yaml('experiments.yaml')
        except Exception as e:
            print(f"\n   ❌ Loading error: {e}")
            raise
    
    def _load_yaml(self, filename: str) -> Dict:
        
        filepath = os.path.join(self.config_dir, filename)
        
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"❌ File not found: {filepath}"
            )
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if config is None:
                raise ValueError(f"❌ Config is empty or invalid: {filename}")
            
            return config
        
        except yaml.YAMLError as e:
            raise ValueError(
                f"❌ YAML parsing error   {filename}:\n{e}"
            )
        
        except Exception as e:
            raise Exception(f"❌ Loading error {filename}: {e}")
    
    def get_config(self, config_name: str) -> Dict:

        configs_section = self.experiments_config.get('configs', {})

        if config_name not in configs_section:
            available = list(configs_section.keys())
            raise ValueError(
                f"❌ Config not found: {config_name}\n"
                f"   Available: {', '.join(available)}"
            )

        specific = configs_section[config_name]

        config = self._merge_configs(self.base_config, specific)

        return config
    
    def get_all_configs(self) -> Dict[str, Dict]:
        
        configs = {}
        
        for exp in self.experiments_config['experiments']:
            name = exp['config']
            configs[name] = self.get_config(name)
        
        return configs
    
    def load_experiments_config(self) -> Dict:
                
        return self.experiments_config
    
    def get_experiment_seeds(self, config_name: str) -> List[int]:
        
        for exp in self.experiments_config['experiments']:
            if exp['config'] == config_name:
                return exp['seeds']
        
        return []

    def _merge_configs(self, base: Dict, specific: Dict) -> Dict:
            merged = copy.deepcopy(base)

            for key, value in specific.items():
                if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                    merged[key].update(copy.deepcopy(value))
                else:
                    merged[key] = copy.deepcopy(value)

            return merged