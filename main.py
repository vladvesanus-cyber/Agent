"""
Application entry point for the drone simulation.

За замовчуванням запускає ПОВНИЙ експеримент: усі конфігурації з
config/experiments.yaml (easy/medium/hard), по 20 прогонів кожна (різні
seeds), агрегує статистику (mean/std) і зберігає все - і сирі результати
кожного прогону, і агреговану статистику - у JSON-файл у results/.
"""

import argparse
import sys

from agents import AdaptiveHeightAgent, BoustrophedonAgent
from simulation import ExperimentRunner
from utils import save_results, get_timestamp_filename


def run_tests() -> int:
    """Run the repository test suite through the application entry point."""
    import pytest

    return pytest.main(["tests", "-q"])


# Фабрики - кожен прогін ExperimentRunner отримує НОВИЙ інстанс агента
# (не один спільний об'єкт, який би тягнув стан з попереднього прогону).
AGENT_FACTORIES = {
    "adaptive": AdaptiveHeightAgent,
    "baseline": lambda: BoustrophedonAgent(cruise_altitude=6.0),
}


def main(argv=None):
    """Run the full experiment suite (or the test suite)."""
    parser = argparse.ArgumentParser(description="Run the drone simulation")

    parser.add_argument(
        "--config",
        choices=["easy", "medium", "hard"],
        default=None,
        help="Обмежитись однією конфігурацією з config/experiments.yaml. "
             "Без цього прапорця виконуються ВСІ три (easy+medium+hard).",
    )

    parser.add_argument(
        "--agent",
        choices=["adaptive", "baseline", "both"],
        default="both",
        help="Який агент(и) тестувати; 'both' порівнює власного агента "
             "з базовим у ТИХ САМИХ умовах (default: both)",
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Перевизначити max_steps для ВСІХ прогонів (напр. для швидкого тесту)",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Шлях до JSON-файлу з результатами "
             "(default: results/experiment_<timestamp>.json)",
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run the test suite and exit",
    )

    args = parser.parse_args(argv)

    if args.test:
        return run_tests()

    selected_agents = (
        AGENT_FACTORIES.items()
        if args.agent == "both"
        else [(args.agent, AGENT_FACTORIES[args.agent])]
    )

    all_results = {}
    all_summaries = {}

    for agent_name, agent_factory in selected_agents:
        print(f"\n{'#'*70}")
        print(f"# АГЕНТ: {agent_name}")
        print(f"{'#'*70}")

        runner = ExperimentRunner(agent_factory, max_steps_override=args.max_steps)
        runner.run_full_experiment(only_config=args.config)

        all_results[agent_name] = runner.results
        all_summaries[agent_name] = runner.summary

    # ===== ПІДСУМКОВЕ ПОРІВНЯННЯ (якщо тестували обох агентів) =====
    if len(all_summaries) > 1:
        print(f"\n{'='*70}")
        print("📊 ПОРІВНЯННЯ АГЕНТІВ (середнє ± стандартне відхилення)")
        print(f"{'='*70}")
        configs = sorted({c for s in all_summaries.values() for c in s})
        for config_name in configs:
            print(f"\n[{config_name}]")
            for agent_name, summaries in all_summaries.items():
                if config_name not in summaries:
                    continue
                s = summaries[config_name]
                print(f"  {agent_name:>10}: "
                      f"експлорація {s['exploration_percent']['mean']:5.1f}% "
                      f"± {s['exploration_percent']['std']:.1f}%, "
                      f"успіх {s['mission_success_rate']*100:.0f}%, "
                      f"колізій {s['collision_count']['mean']:.2f}")

    # ===== ЗБЕРЕЖЕННЯ РЕЗУЛЬТАТІВ НА ДИСК =====
    output_path = args.output or f"results/experiment_{get_timestamp_filename()}.json"
    save_results(
        {
            "results": all_results,     # сирі результати кожного прогону (зберігає "perебіг" кожного запуску)
            "summary": all_summaries,    # агреговане mean/std/min/max по кожній конфігурації
        },
        output_path,
        format="json",
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())