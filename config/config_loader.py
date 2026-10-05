"""
ConfigLoader - завантаження та управління конфігами
"""

import copy
import yaml
from pathlib import Path
from typing import Dict, List
import os


class ConfigLoader:
    """
    Завантажує конфіги з YAML файлів
    Підтримує базову конфіку + спеціалізовані конфіки
    """
    
    def __init__(self, config_dir: str = 'config'):
        """
        Args:
            config_dir: Директорія з конфіками
        """
        
        # ===== ДІАГНОСТИКА =====
        print(f"\n🔍 ДІАГНОСТИКА КОНФІГА:")
        print(f"   Поточна директорія: {os.getcwd()}")
        
        # Використовувати абсолютний шлях
        if os.path.isabs(config_dir):
            self.config_dir = config_dir
        else:
            self.config_dir = os.path.join(os.getcwd(), config_dir)
        
        self.config_dir = os.path.abspath(self.config_dir)
        
        print(f"   Шукаємо конфіг в: {self.config_dir}")
        
        # Переконатись що директорія існує
        if not os.path.isdir(self.config_dir):
            print(f"   ❌ Директорія НЕ існує!")
            
            raise FileNotFoundError(
                f"❌ Директорія конфіга не знайдена: {self.config_dir}\n"
                f"   Переконайтесь що вона існує!"
            )
        
        print(f"   ✅ Директорія знайдена")
        
        # Перевірити файли
        env_file = os.path.join(self.config_dir, 'environment.yaml')
        exp_file = os.path.join(self.config_dir, 'experiments.yaml')
        
        print(f"\n   Шукаємо файли:")
        print(f"   - {env_file}: {'✅ ІСНУЄ' if os.path.exists(env_file) else '❌ НЕ ІСНУЄ'}")
        print(f"   - {exp_file}: {'✅ ІСНУЄ' if os.path.exists(exp_file) else '❌ НЕ ІСНУЄ'}")
        
        if not os.path.exists(env_file) or not os.path.exists(exp_file):
            print(f"\n   ❌ Деякі файли відсутні!")
            raise FileNotFoundError(
                f"❌ Файли конфіга не знайдені\n"
                f"   Потрібні файли:\n"
                f"   - {env_file}\n"
                f"   - {exp_file}"
            )
        
        print(f"\n   ✅ Всі файли знайдені!\n")
        
        # ===== ЗАВАНТАЖИТИ КОНФІКИ =====
        try:
            self.base_config = self._load_yaml('environment.yaml')
            self.experiments_config = self._load_yaml('experiments.yaml')
            print("   ✅ Конфіги успішно завантажені!\n")
        except Exception as e:
            print(f"\n   ❌ Помилка при завантаженні: {e}")
            raise
    
    def _load_yaml(self, filename: str) -> Dict:
        """
        Завантажити YAML файл
        
        Args:
            filename: Назва файлу
        
        Returns:
            Словник конфігурації
        """
        
        filepath = os.path.join(self.config_dir, filename)
        
        print(f"   📂 Завантажуємо: {filepath}")
        
        # Перевірити чи файл існує
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"❌ Файл не знайдено: {filepath}"
            )
        
        try:
            # Відкрити файл з правильним кодуванням
            with open(filepath, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if config is None:
                raise ValueError(f"❌ Конфіг пустий або помилковий: {filename}")
            
            print(f"      ✅ {len(str(config))} байт завантажено")
            return config
        
        except yaml.YAMLError as e:
            raise ValueError(
                f"❌ Помилка парсингу YAML в файлі {filename}:\n{e}"
            )
        
        except Exception as e:
            raise Exception(f"❌ Помилка завантаження {filename}: {e}")
    
    def get_config(self, config_name: str) -> Dict:
        """
        Отримати конфіку за назвою (easy, medium, hard)

        Args:
            config_name: Назва конфіки (easy/medium/hard)

        Returns:
            Об'єднана конфіка (базова + спеціалізована)

        Example:
            config = loader.get_config('medium')
        """

        # ===== ЗНАЙТИ ПЕРЕВИЗНАЧЕННЯ У СЕКЦІЇ 'configs' =====
        # УВАГА: раніше тут шукалось у experiments_config['experiments'] -
        # але там лежать лише {name, config, runs, seeds} для кожного
        # прогону експерименту. Самі перевизначення map/terrain/drone/
        # physics/episode лежать у experiments.yaml під configs.<назва>.
        # Через цю помилку easy/medium/hard завжди повертали ОДНАКОВУ
        # (базову) конфігурацію - жодне перевизначення ніколи не застосовувалось.
        configs_section = self.experiments_config.get('configs', {})

        if config_name not in configs_section:
            available = list(configs_section.keys())
            raise ValueError(
                f"❌ Конфіка не знайдена: {config_name}\n"
                f"   Доступні: {', '.join(available)}"
            )

        specific = configs_section[config_name]

        # Об'єднати базову конфіку з специфічною (глибока копія -
        # inакше повторні виклики get_config() на тому самому loader'і
        # могли б накопичувати перевизначення одне на одному).
        config = self._merge_configs(self.base_config, specific)

        print(f"✅ Конфіка обрана: {config_name}")
        return config
    
    def get_all_configs(self) -> Dict[str, Dict]:
        """
        Отримати ВСІ три конфіки
        
        Returns:
            Словник {назва: конфіка}
        """
        
        configs = {}
        
        for exp in self.experiments_config['experiments']:
            name = exp['config']
            configs[name] = self.get_config(name)
        
        return configs
    
    def load_experiments_config(self) -> Dict:
        """
        Отримати конфіку експериментів
        
        Returns:
            Словник з всіма експериментами
        """
        
        return self.experiments_config
    
    def get_experiment_seeds(self, config_name: str) -> List[int]:
        """
        Отримати seeds для конкретної конфіки
        
        Args:
            config_name: Назва конфіки (easy/medium/hard)
        
        Returns:
            Список seeds
        """
        
        for exp in self.experiments_config['experiments']:
            if exp['config'] == config_name:
                return exp['seeds']
        
        return []
    
    def print_info(self):
        """Вивести інформацію про конфіки"""
        
        print("\n" + "="*70)
        print("📊 ІНФОРМАЦІЯ ПРО КОНФІКИ")
        print("="*70)
        
        for exp in self.experiments_config['experiments']:
            print(f"\n📌 {exp['name']}")
            print(f"   Config: {exp['config']}")
            print(f"   Runs: {exp['runs']}")
            print(f"   Map: {exp['map']['width']}x{exp['map']['height']}")
            print(f"   Battery: {exp['drone']['battery_capacity']}%")
            print(f"   Obstacles: {exp['terrain']['obstacle_ratio']*100:.0f}%")
            print(f"   Max steps: {exp['episode']['max_steps']}")

    def _merge_configs(self, base: Dict, specific: Dict) -> Dict:
            """
            Об'єднати два конфіги (specific перевизначає base).

            Глибока копія: base.copy() - це ЛИШЕ поверхнева копія, вкладені
            словники (map/terrain/drone/...) лишались ТИМИ Ж об'єктами, що й
            у self.base_config. merged[key].update(value) тоді мутував би
            сам self.base_config, і наступний виклик get_config() для
            ІНШОЇ конфігурації отримав би залишки попередньої.
            """
            merged = copy.deepcopy(base)

            for key, value in specific.items():
                if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                    merged[key].update(copy.deepcopy(value))
                else:
                    merged[key] = copy.deepcopy(value)

            return merged