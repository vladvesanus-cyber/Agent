"""
ExperimentRunner - запускає декілька симуляцій з різними seeds
"""

import copy
from typing import Callable, Dict, List, Optional

from config import ConfigLoader
from tests import Statistics
from .simulation import Simulator


class ExperimentRunner:
    """
    Запускає експерименти:
    - 3 конфігурації (easy, medium, hard) - або лише одну через only_config
    - N запусків кожної (різні seeds, з config/experiments.yaml)
    - Кожен прогін - це НОВИЙ інстанс агента (незалежне випробування)
    - Агрегує статистику (mean/std) через tests.metrics.Statistics
    """

    def __init__(self, agent_factory: Callable, max_steps_override: Optional[int] = None):
        """
        Args:
            agent_factory: функція БЕЗ аргументів, що повертає новий
                інстанс агента (напр. `AdaptiveHeightAgent` як клас,
                або `lambda: BoustrophedonAgent(cruise_altitude=6.0)`).

                Раніше сюди передавали вже створений об'єкт агента і
                використовували його ПОВТОРНО для всіх 20 seed-ів одної
                конфігурації. Але AdaptiveHeightAgent/BoustrophedonAgent
                тримають внутрішній стан (last_position, direction,
                home_position), який між "незалежними" прогонами ніколи
                не скидався - перший epizod міг непомітно впливати на
                другий. Фабрика гарантує, що кожен прогін стартує з
                чистого агента.
            max_steps_override: якщо задано - перевизначає max_steps з
                конфіга для ВСІХ прогонів (напр. для швидкого smoke-тесту).
        """
        self.config_loader = ConfigLoader()
        self.agent_factory = agent_factory
        self.max_steps_override = max_steps_override
        self.results: Dict[str, List[Dict]] = {}
        self.summary: Dict[str, Dict] = {}

    def run_full_experiment(self, only_config: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        Запустити експерименти.

        Args:
            only_config: якщо вказано ('easy'/'medium'/'hard') - виконати
                ТІЛЬКИ цю конфігурацію. Якщо None - виконати всі три
                (як того вимагає завдання: мінімум 3 конфігурації).
        """

        experiments_config = self.config_loader.load_experiments_config()

        for experiment in experiments_config['experiments']:
            config_name = experiment['config']

            if only_config is not None and config_name != only_config:
                continue

            seeds = experiment['seeds']

            print(f"\n{'='*70}")
            print(f"🚀 ЕКСПЕРИМЕНТ: {experiment['name']}")
            print(f"   Конфіг: {config_name}")
            print(f"   Запусків: {len(seeds)}")
            print(f"{'='*70}\n")

            results = self._run_configuration(config_name, seeds)
            self.results[config_name] = results
            self.summary[config_name] = self._aggregate(results)

            self._print_summary(config_name, self.summary[config_name])

        return self.results

    def _run_configuration(self, config_name: str, seeds: List[int]) -> List[Dict]:
        """
        Запустити конфіг N разів з різними seeds.
        Кожен прогін отримує СВОЮ копію конфіга і СВІЖОГО агента.
        """

        base_config = self.config_loader.get_config(config_name)
        results = []

        for i, seed in enumerate(seeds):
            print(f"  Запуск {i+1}/{len(seeds)} (seed={seed})...", end=" ")

            # Власна копія конфіга на кожен прогін - inакше
            # config['episode']['seed'] = seed мутував би ОДИН спільний
            # dict, яким користуються всі наступні прогони.
            config = copy.deepcopy(base_config)
            config['episode']['seed'] = seed
            if self.max_steps_override is not None:
                config['episode']['max_steps'] = self.max_steps_override

            agent = self.agent_factory()  # завжди новий, "чистий" агент

            simulator = Simulator(config, agent)
            result = simulator.run_episode()
            results.append(result)

            print(f"✅ Експлорація: {result['exploration_ratio']*100:.1f}% "
                  f"(кроків: {result['total_steps']}, "
                  f"успіх: {'ТАК' if result['mission_success'] else 'ні'})")

        return results

    @staticmethod
    def _aggregate(results: List[Dict]) -> Dict:
        """
        Агрегована статистика по N прогонах - mean/std/min/max через
        tests.metrics.Statistics (цей клас раніше був написаний, але
        ніде не викликався поза unit-тестами).
        """

        def stat(values: List[float]) -> Dict:
            mn, mx = Statistics.calculate_min_max(values)
            return {
                'mean': Statistics.calculate_mean(values),
                'std': Statistics.calculate_std(values),
                'min': mn,
                'max': mx,
            }

        explorations = [r['exploration_ratio'] * 100 for r in results]
        steps = [r['total_steps'] for r in results]
        batteries = [r['final_battery'] for r in results]
        healths = [r['final_health'] for r in results]
        collisions = [r['collision_count'] for r in results]
        bad_scans = [r.get('bad_scan_count', 0) for r in results]
        successes = [1.0 if r['mission_success'] else 0.0 for r in results]

        return {
            'runs': len(results),
            'exploration_percent': stat(explorations),
            'steps': stat(steps),
            'final_battery_percent': stat(batteries),
            'final_health_percent': stat(healths),
            'collision_count': stat(collisions),
            'bad_scan_count': stat(bad_scans),
            'mission_success_rate': Statistics.calculate_mean(successes),
        }

    @staticmethod
    def _print_summary(config_name: str, summary: Dict):
        print(f"\n📊 СТАТИСТИКА '{config_name}' ({summary['runs']} прогонів):")
        print(f"   Експлорація:     {summary['exploration_percent']['mean']:6.1f}% "
              f"± {summary['exploration_percent']['std']:.1f}%")
        print(f"   Кроків:          {summary['steps']['mean']:6.1f} "
              f"± {summary['steps']['std']:.1f}")
        print(f"   Фін. батарея:    {summary['final_battery_percent']['mean']:6.1f}% "
              f"± {summary['final_battery_percent']['std']:.1f}%")
        print(f"   Фін. здоров'я:   {summary['final_health_percent']['mean']:6.1f}% "
              f"± {summary['final_health_percent']['std']:.1f}%")
        print(f"   Колізій:         {summary['collision_count']['mean']:6.2f} "
              f"± {summary['collision_count']['std']:.2f}")
        print(f"   Успішних місій:  {summary['mission_success_rate']*100:.0f}%")