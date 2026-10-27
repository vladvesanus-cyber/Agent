
import argparse
import sys

from agents import AdaptiveHeightAgent, BoustrophedonAgent
from simulation import ExperimentRunner
from utils import save_results, get_timestamp_filename


def run_tests() -> int:
    """Run the repository test suite through the application entry point."""
    import pytest

    return pytest.main(["tests", "-q"])

AGENT_FACTORIES = {
    "adaptive": AdaptiveHeightAgent,
    "baseline": lambda: BoustrophedonAgent(cruise_altitude=0.0),
    "baseline6": lambda: BoustrophedonAgent(cruise_altitude=6.0),  # fairer baseline (6 m, scan 100 %)
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
        choices=["adaptive", "baseline", "baseline6", "both", "all"],
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
        if args.agent == "all"
        else [(n, AGENT_FACTORIES[n]) for n in ("adaptive", "baseline")]
        if args.agent == "both"
        else [(args.agent, AGENT_FACTORIES[args.agent])]
    )

    all_results = {}
    all_summaries = {}

    for agent_name, agent_factory in selected_agents:

        runner = ExperimentRunner(agent_factory, max_steps_override=args.max_steps)
        runner.run_full_experiment(only_config=args.config)

        all_results[agent_name] = runner.results
        all_summaries[agent_name] = runner.summary

    if len(all_summaries) > 1:
        configs = sorted({c for s in all_summaries.values() for c in s})
        for config_name in configs:
            print(f"\n[{config_name}]")
            for agent_name, summaries in all_summaries.items():
                if config_name not in summaries:
                    continue
                s = summaries[config_name]
                print(f"  {agent_name:>10}: "
                      f"exploration {s['exploration_percent']['mean']:5.1f}% "
                      f"± {s['exploration_percent']['std']:.1f}%, "
                      f"success {s['mission_success_rate']*100:.0f}%, "
                      f"collision {s['collision_count']['mean']:.2f}")

    output_path = args.output or f"results/experiment_{get_timestamp_filename()}.json"
    save_results(
        {
            "results": all_results,     
            "summary": all_summaries, 
        },
        output_path,
        format="json",
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())