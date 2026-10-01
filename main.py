"""
Запуск з reproducibility
"""

from utils import ConfigLoader
from simulation import Simulator
from agents import AdaptiveHeightAgent
from utils import set_seed
from tests import Metrics, DataLogger


def main():
    """Запуск одного експерименту з reproducibility"""
    
    loader = ConfigLoader()
    config = loader.get_config('medium')
    
    # ===== ВСТАНОВИТИ SEED =====
    seed = config['episode']['seed']
    set_seed(seed)
    print(f"🌱 Seed встановлено: {seed}")
    
    # Запуск симуляції
    agent = AdaptiveHeightAgent()
    simulator = Simulator(config, agent)
    result = simulator.run_episode()
    
    # Розрахувати метрики
    metrics = Metrics.calculate_all_metrics(result)
    
    print(f"\n📊 РЕЗУЛЬТАТИ:")
    print(f"   Експлорація: {metrics['exploration_ratio']*100:.1f}%")
    print(f"   Performance: {metrics['performance']:.1f}")
    print(f"   Батарея: {metrics['final_battery']:.1f}%")
    
    # Зберегти результат
    logger = DataLogger()
    logger.save_result({**result, 'metrics': metrics}, 'medium', 1)


def test_reproducibility():
    """
    Тест: запустити ДВА РАЗИ з однаковим seed
    Результати повинні бути ТОЧНО ОДИНАКОВІ
    """
    
    from utils import verify_reproducibility
    
    loader = ConfigLoader()
    config = loader.get_config('medium')
    seed = config['episode']['seed']
    
    # Запуск 1
    set_seed(seed)
    agent1 = AdaptiveHeightAgent()
    sim1 = Simulator(config, agent1)
    result1 = sim1.run_episode()
    
    # Запуск 2
    set_seed(seed)
    agent2 = AdaptiveHeightAgent()
    sim2 = Simulator(config, agent2)
    result2 = sim2.run_episode()
    
    # Перевірка
    if verify_reproducibility(result1, result2):
        print("✅ REPRODUCIBILITY: OK - результати однакові!")
    else:
        print("❌ REPRODUCIBILITY: FAILED - результати різні!")
        print(f"   Експлорація 1: {result1['exploration_ratio']}")
        print(f"   Експлорація 2: {result2['exploration_ratio']}")


if __name__ == '__main__':
    main()
    # test_reproducibility()