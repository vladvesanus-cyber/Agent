"""
Головний файл для запуску

Тепер конфігурація береться з config/experiments.yaml (easy/medium/hard)
замість захардкодженого 'hard'. Обрати іншу - прапорцем --config.
"""

import argparse

from config import ConfigLoader
from simulation import Simulator
from agents import AdaptiveHeightAgent, BoustrophedonAgent
from utils import set_seed


def main():
    """Точка входу"""

    parser = argparse.ArgumentParser(description="Запуск симуляції дрона")
    parser.add_argument('--config', choices=['easy', 'medium', 'hard'], default='medium',
                        help="яку конфігурацію з config/experiments.yaml використати (default: medium)")
    parser.add_argument('--agent', choices=['adaptive', 'baseline'], default='adaptive',
                        help="adaptive = AdaptiveHeightAgent, baseline = BoustrophedonAgent (default: adaptive)")
    parser.add_argument('--seed', type=int, default=None,
                        help="перевизначити seed із конфіга")
    parser.add_argument('--max-steps', type=int, default=None,
                        help="перевизначити max_steps із конфіга")
    args = parser.parse_args()

    # ===== ЗАВАНТАЖИТИ КОНФІГ =====
    print("\n📂 Завантаження конфіга...")
    loader = ConfigLoader(config_dir='config')

    config = loader.get_config(args.config)

    if args.seed is not None:
        config['episode']['seed'] = args.seed
    if args.max_steps is not None:
        config['episode']['max_steps'] = args.max_steps

    # Встановити seed
    seed = config['episode']['seed']
    set_seed(seed)
    print(f"🌱 Seed: {seed}")

    # ===== ДІАГНОСТИКА =====
    print(f"\n📊 КОНФІГ: '{args.config}'")
    print(f"   Карта: {config['map']['width']}x{config['map']['height']}")
    print(f"   Стартова позиція: ({config['drone']['start_x']}, {config['drone']['start_y']})")
    print(f"   Батарея: {config['drone']['battery_capacity']}%")
    print(f"   Макс кроків: {config['episode']['max_steps']}")
    print(f"   Перешкод: {config['terrain']['obstacle_ratio']*100:.0f}%")
    print(f"   Агент: {args.agent}")

    # Створити симулятор
    agent = AdaptiveHeightAgent() if args.agent == 'adaptive' else BoustrophedonAgent(cruise_altitude=6.0)
    simulator = Simulator(config, agent)

    # Запустити
    result = simulator.run_episode()

    # ===== РЕЗУЛЬТАТИ =====
    print(f"\n✅ РЕЗУЛЬТАТ:")
    print(f"   Кроків: {result['total_steps']}")
    print(f"   Експлорація: {result['exploration_ratio']*100:.1f}%")
    print(f"   Досліджено клітин: {len(result['explored_cells'])}")
    print(f"   Поганих кадрів (не зараховано): {result['bad_scan_count']}")
    print(f"   Батарея: {result['final_battery']:.1f}%")
    print(f"   Здоров'я: {result['final_health']:.1f}%")
    print(f"   Колізій: {result['collision_count']}")
    print(f"   Фінальна позиція: {result['final_position']}")
    print(f"   Місія успішна: {'✅ ТАК' if result['mission_success'] else '❌ НІ'}")


if __name__ == '__main__':
    main()