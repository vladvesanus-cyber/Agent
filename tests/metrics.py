import numpy as np
from typing import Dict, List
import json
from pathlib import Path


class Metrics:
    
    @staticmethod
    def calculate_performance(result: Dict) -> float:
        
        exploration = result['exploration_ratio']
        steps = result['total_steps']
        energy_used = 100 - result.get('final_battery', 0)
        
        safe_return = 1.0 if result.get('returned_home', False) else 0.0
        
        performance = (
            exploration * 1000 +
            safe_return * 100 +
            - energy_used * 2 +
            - steps * 0.1
        )
        
        return performance
    
    @staticmethod
    def calculate_all_metrics(result: Dict) -> Dict:
        
        return {
            'performance': Metrics.calculate_performance(result),
            'exploration_ratio': result['exploration_ratio'],
            'explored_cells': result['explored_cells'],
            'total_steps': result['total_steps'],
            'total_reward': result['total_reward'],
            'final_battery': result.get('final_battery', 0),
            'final_health': result.get('final_health', 0),
            'collision_count': result.get('collision_count', 0),
            'motor_efficiency': result.get('motor_efficiency', 100),
            'sensor_accuracy': result.get('sensor_accuracy', 100),
            'returned_home': result.get('returned_home', False)
        }


class Statistics:
    
    @staticmethod
    def calculate_mean(values: List[float]) -> float:
        return float(np.mean(values))
    
    @staticmethod
    def calculate_std(values: List[float]) -> float:
        return float(np.std(values))
    
    @staticmethod
    def calculate_min_max(values: List[float]) -> tuple:
        return (float(np.min(values)), float(np.max(values)))
    
    @staticmethod
    def aggregate_results(all_results: List[Dict]) -> Dict:
        
        if not all_results:
            return {}
        
        performances = [r.get('performance', 0) for r in all_results]
        explorations = [r.get('exploration_ratio', 0) for r in all_results]
        steps = [r.get('total_steps', 0) for r in all_results]
        batteries = [r.get('final_battery', 0) for r in all_results]
        healths = [r.get('final_health', 0) for r in all_results]
        
        return {
            'performance': {
                'mean': Statistics.calculate_mean(performances),
                'std': Statistics.calculate_std(performances),
                'min': np.min(performances),
                'max': np.max(performances)
            },
            'exploration': {
                'mean': Statistics.calculate_mean(explorations),
                'std': Statistics.calculate_std(explorations),
                'min': np.min(explorations),
                'max': np.max(explorations)
            },
            'steps': {
                'mean': Statistics.calculate_mean(steps),
                'std': Statistics.calculate_std(steps),
                'min': np.min(steps),
                'max': np.max(steps)
            },
            'battery': {
                'mean': Statistics.calculate_mean(batteries),
                'std': Statistics.calculate_std(batteries),
                'min': np.min(batteries),
                'max': np.max(batteries)
            },
            'health': {
                'mean': Statistics.calculate_mean(healths),
                'std': Statistics.calculate_std(healths),
                'min': np.min(healths),
                'max': np.max(healths)
            },
            'total_runs': len(all_results)
        }


class DataLogger:
    def __init__(self, output_dir: str = 'results'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def save_result(self, result: Dict, config_name: str, run_number: int):
        
        config_dir = self.output_dir / config_name
        config_dir.mkdir(exist_ok=True)
        
        metrics = Metrics.calculate_all_metrics(result)
        
        full_data = {
            **result,
            'metrics': metrics
        }
        
        filename = config_dir / f'run_{run_number:03d}.json'
        with open(filename, 'w') as f:
            json.dump(full_data, f, indent=2)
    
    def save_summary(self, all_results: Dict[str, List[Dict]], config_name: str):
        
        results = all_results[config_name]
        stats = Statistics.aggregate_results(results)
        
        config_dir = self.output_dir / config_name
        
        summary = {
            'config': config_name,
            'statistics': stats,
            'results_count': len(results)
        }
        
        filename = config_dir / 'summary.json'
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary
    
    def print_summary(self, summary: Dict):
        
        print(f"\n{'='*70}")
        print(f"📊 {summary['config'].upper()}")
        print(f"{'='*70}")
        
        stats = summary['statistics']
        
        print(f"\nPerformance:")
        print(f"  Mean: {stats['performance']['mean']:.1f} "
              f"(±{stats['performance']['std']:.1f})")
        print(f"  Range: [{stats['performance']['min']:.1f}, "
              f"{stats['performance']['max']:.1f}]")
        
        print(f"\nExploration:")
        print(f"  Mean: {stats['exploration']['mean']*100:.1f}% "
              f"(±{stats['exploration']['std']*100:.1f}%)")
        
        print(f"\nBattery:")
        print(f"  Mean: {stats['battery']['mean']:.1f}% "
              f"(±{stats['battery']['std']:.1f}%)")
        
        print(f"\nHealth:")
        print(f"  Mean: {stats['health']['mean']:.1f}% "
              f"(±{stats['health']['std']:.1f}%)")
        
        print(f"\nSteps:")
        print(f"  Mean: {stats['steps']['mean']:.0f} "
              f"(±{stats['steps']['std']:.0f})")