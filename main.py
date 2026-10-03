"""
Головний файл для запуску
"""

from config import ConfigLoader
from simulation import Simulator
from agents import AdaptiveHeightAgent
from utils import set_seed


def main():
    """Точка входу"""
    
        # ===== ЗАВАНТАЖИТИ КОНФІГ =====
    print("\n📂 Завантаження конфіга...")
    loader = ConfigLoader(config_dir='config')
        
        
    config = loader.get_config('hard')
        
        # Встановити seed
    seed = config['episode']['seed']
    set_seed(seed)
    print(f"🌱 Seed: {seed}")
        
        # ===== ДІАГНОСТИКА =====
    print(f"\n📊 КОНФІГ:")
    print(f"   Карта: {config['map']['width']}x{config['map']['height']}")
    print(f"   Стартова позиція: ({config['drone']['start_x']}, {config['drone']['start_y']})")
    print(f"   Батарея: {config['drone']['battery_capacity']}%")
    print(f"   Макс кроків: {config['episode']['max_steps']}")
    print(f"   Перешкод: {config['terrain']['obstacle_ratio']*100:.0f}%")
    
        
        # Створити симулятор
    agent = AdaptiveHeightAgent()
    simulator = Simulator(config, agent)
        
        # Запустити
    result = simulator.run_episode()
        
        # ===== РЕЗУЛЬТАТИ =====
    print(f"\n✅ РЕЗУЛЬТАТ:")
    print(f"   Кроків: {result['total_steps']}")
    print(f"   Експлорація: {result['exploration_ratio']*100:.1f}%")
    print(f"   Досліджено клітин: {result['explored_cells']}")
    print(f"   Батарея: {result['final_battery']:.1f}%")
    print(f"   Здоров'я: {result['final_health']:.1f}%")
    print(f"   Колізій: {result['collision_count']}")
    print(f"   Фінальна позиція: {result['final_position']}")

if __name__ == '__main__':
    main()