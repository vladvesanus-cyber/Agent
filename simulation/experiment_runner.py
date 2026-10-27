import copy
from typing import Callable, Dict, List, Optional

from config import ConfigLoader
from utils import set_seed
from tests import Statistics
from .simulation import Simulator


class ExperimentRunner:

    def __init__(self, agent_factory: Callable, max_steps_override: Optional[int] = None):
        self.config_loader = ConfigLoader()
        self.agent_factory = agent_factory
        self.max_steps_override = max_steps_override
        self.results: Dict[str, List[Dict]] = {}
        self.summary: Dict[str, Dict] = {}

    def run_full_experiment(self, only_config: Optional[str] = None) -> Dict[str, List[Dict]]:

        experiments_config = self.config_loader.load_experiments_config()

        for experiment in experiments_config['experiments']:
            config_name = experiment['config']

            if only_config is not None and config_name != only_config:
                continue

            seeds = experiment['seeds']

            results = self._run_configuration(config_name, seeds)
            self.results[config_name] = results
            self.summary[config_name] = self._aggregate(results)

            self._print_summary(config_name, self.summary[config_name])

        return self.results

    def _run_configuration(self, config_name: str, seeds: List[int]) -> List[Dict]:

        base_config = self.config_loader.get_config(config_name)
        results = []

        for i, seed in enumerate(seeds):

            config = copy.deepcopy(base_config)
            config['episode']['seed'] = seed
            if self.max_steps_override is not None:
                config['episode']['max_steps'] = self.max_steps_override

            # seed numpy + python random -> agent's random.choice is reproducible too
            set_seed(seed)
            agent = self.agent_factory()

            simulator = Simulator(config, agent)
            result = simulator.run_episode()
            results.append(result)

        return results

    @staticmethod
    def _aggregate(results: List[Dict]) -> Dict:

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
        print(f"\n📊 Stat '{config_name}' ({summary['runs']} runs):")
        print(f"   Exploration:     {summary['exploration_percent']['mean']:6.1f}% "
              f"± {summary['exploration_percent']['std']:.1f}%")
        print(f"   Steps:            {summary['steps']['mean']:6.1f} "
              f"± {summary['steps']['std']:.1f}")
        print(f"   Final Battery:   {summary['final_battery_percent']['mean']:6.1f}% "
              f"± {summary['final_battery_percent']['std']:.1f}%")
        print(f"   Final Health:    {summary['final_health_percent']['mean']:6.1f}% "
              f"± {summary['final_health_percent']['std']:.1f}%")
        print(f"   Collisions:      {summary['collision_count']['mean']:6.2f} "
              f"± {summary['collision_count']['std']:.2f}")
        print(f"   Successful Missions:  {summary['mission_success_rate']*100:.0f}%")