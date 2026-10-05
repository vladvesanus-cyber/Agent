"""
Terminalova animacia letu drona - vidite priamo v konzole, ako sa dron
krok po kroku pohybuje po mape, kde su stromy/prekazky/voda/hory, a co
sa deje s baterkou a zdravim.

Spustenie:
    cd Project1
    python demo/terminal_animation.py                        # demo mapa, adaptivny agent
    python demo/terminal_animation.py --config easy           # konfig z config/experiments.yaml (ako main.py)
    python demo/terminal_animation.py --config hard --agent baseline
    python demo/terminal_animation.py --speed 0.02            # rychlejsie
    python demo/terminal_animation.py --seed 11                # ina mapa (ten isty config)

--config easy/medium/hard nacita presne tu istu konfiguraciu ako
main.py --config ... (cez ConfigLoader z config/experiments.yaml).
--config demo (default) pouziva zahustenu ukazkovu mapu z demo/demo.py
(vela stromov - dobre vidno zrazky s konarmi), ktora NIE je v
config/experiments.yaml.

Vnutorne pouziva presne tu istu logiku kroku ako Simulator.run_episode()
(simulation/simulation.py) - len po kazdom kroku vykresli ramec navyse,
takze vysledky su rovnake, aky by boli pri bezom run_episode().
"""

import argparse
import copy
import importlib.util
import os
import sys
import time

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
sys.path.insert(0, _PROJECT_ROOT)

from config import ConfigLoader
from simulation import Simulator
from agents import AdaptiveHeightAgent, BoustrophedonAgent
from utils import set_seed

# ===== ANSI =====
RESET = "\033[0m"
CLEAR = "\033[H\033[2J"
DIM = "\033[2m"
BOLD = "\033[1m"

COLOR_FREE = "\033[92m"       # zelena (svetla)
COLOR_OBSTACLE = "\033[33m"   # hneda/zlta
COLOR_TREE = "\033[32m"       # zelena (tmava)
COLOR_WATER = "\033[36m"      # cyan
COLOR_MOUNTAIN = "\033[37m"   # siva
COLOR_TRAIL = "\033[90m"      # tmavosiva
COLOR_DRONE_LOW = "\033[91m"     # cervena - nizko (riziko)
COLOR_DRONE_MID = "\033[93m"     # zlta - stredna vyska
COLOR_DRONE_HIGH = "\033[95m"    # fialova - vysoko
COLOR_HOME = "\033[94m"       # modra

TERRAIN_SYMBOLS = {
    0: (COLOR_FREE, '.'),
    1: (COLOR_OBSTACLE, '#'),
    2: (COLOR_TREE, '♣'),
    3: (COLOR_WATER, '~'),
    4: (COLOR_MOUNTAIN, '^'),
}


def drone_color(z):
    if z <= 2:
        return COLOR_DRONE_LOW
    if z <= 6:
        return COLOR_DRONE_MID
    return COLOR_DRONE_HIGH


def render(env, drone, home, trail, step, iteration, max_steps, last_event):
    lines = [CLEAR]

    header = (f"{BOLD}Krok {iteration}/{max_steps}{RESET}   "
              f"Pozicia ({int(drone.position[0])},{int(drone.position[1])})  "
              f"Vyska {drone.position[2]:.1f}m   "
              f"Baterka {drone.battery.get_remaining_range():5.1f}%   "
              f"Zdravie {drone.health_monitor.get_overall_health():5.1f}%   "
              f"Pokrytie {len(env.visited_cells) / (env.width * env.height) * 100:4.1f}%")
    lines.append(header)
    if last_event:
        lines.append(f"{BOLD}\033[91m>> {last_event}{RESET}")
    else:
        lines.append("")
    lines.append("")

    dx, dy = int(drone.position[0]), int(drone.position[1])
    hx, hy = home

    for y in range(env.height):
        row = []
        for x in range(env.width):
            if x == dx and y == dy:
                c = drone_color(drone.position[2])
                row.append(f"{c}{BOLD}D{RESET}")
            elif x == hx and y == hy:
                row.append(f"{COLOR_HOME}{BOLD}H{RESET}")
            elif (x, y) in trail:
                row.append(f"{COLOR_TRAIL}·{RESET}")
            else:
                cell = int(env.world_map[y, x])
                color, sym = TERRAIN_SYMBOLS.get(cell, (RESET, '?'))
                row.append(f"{color}{sym}{RESET}")
        lines.append(' '.join(row))

    lines.append("")
    legend = (f"{COLOR_FREE}.{RESET} volno  "
              f"{COLOR_OBSTACLE}#{RESET} prekazka  "
              f"{COLOR_TREE}♣{RESET} strom  "
              f"{COLOR_WATER}~{RESET} voda  "
              f"{COLOR_MOUNTAIN}^{RESET} hora  "
              f"{COLOR_HOME}H{RESET} baza  "
              f"{COLOR_TRAIL}·{RESET} navstivene  "
              f"{COLOR_DRONE_MID}D{RESET} dron (farba = vyska)")
    lines.append(legend)

    sys.stdout.write('\n'.join(lines) + '\n')
    sys.stdout.flush()


def animate(agent, config, delay, max_render_steps=None):
    """
    Zopakuje presne tu istu logiku ako Simulator.run_episode(), ale po
    kazdej iteracii vykresli ramec. Vyuziva priamo privatne metody
    Simulatora, aby vysledok bol identicky s bezanim run_episode().
    """
    set_seed(config['episode']['seed'])
    sim = Simulator(config, agent)
    sim.drone.take_off()
    sim.drone.reset()

    home = (sim.env.start_x, sim.env.start_y)
    trail = set()
    done = False
    iteration = 0
    last_event = None
    max_steps = config['episode']['max_steps']
    if max_render_steps:
        max_steps = min(max_steps, max_render_steps)

    try:
        while not done and sim.step_count < max_steps:
            iteration += 1
            observation = sim._get_observation()
            action = agent.decide(observation)

            target_altitude = action.get('altitude', 5.0)
            dx, dy, dz = action['move']

            new_x = sim.drone.position[0] + dx
            new_y = sim.drone.position[1] + dy

            last_event = None

            if not (0 <= new_x < sim.env.width and 0 <= new_y < sim.env.height):
                collision_detected = True
                terrain = "wall"
                damage = 1.0
                last_event = "Naraz do hranice mapy!"
            else:
                collision_detected = sim.env.detect_collision(new_x, new_y, sim.drone.position[2])
                if collision_detected:
                    terrain = sim.env.classify_terrain(new_x, new_y)
                    damage = sim.env.calculate_collision_damage(terrain, sim.drone.position[2])
                    label = {
                        'tree_branches': 'Zachytenie o konar stromu!',
                        'hard_obstacle': 'Naraz do prekazky!',
                        'water': 'Pad do vody!',
                        'mountain': 'Naraz do hory!',
                    }.get(terrain, f'Kolizia ({terrain})')
                    last_event = label

            if collision_detected:
                sim.env.report_collision(terrain, damage, new_x, new_y, sim.drone.position[2])
                sim.drone.record_collision(terrain, damage)
                sim.drone.update_health(
                    energy_consumed=1.0,
                    motor_stress=[0.3, 0.3, 0.3, 0.3],
                    altitude=sim.drone.get_altitude(),
                    collision_occurred=True,
                    collision_damage=damage,
                )
            else:
                move_result = sim.drone.move(dx, dy, dz, target_altitude=target_altitude)
                if move_result:
                    sim.env.drone_x = sim.drone.position[0]
                    sim.env.drone_y = sim.drone.position[1]
                    sim.env.drone_z = sim.drone.position[2]

                    # Zapocitat bunku ako preskumanu LEN ked je sken dost kvalitny
                    # (prilis nizko = prach, prilis vysoko = horsie rozlisenie).
                    scan_quality = sim.env.calculate_scan_quality(sim.drone.position[2])
                    if scan_quality >= sim.env.min_scan_quality:
                        sim.env.visited_cells.add((int(sim.drone.position[0]), int(sim.drone.position[1])))
                    else:
                        sim.bad_scan_count += 1
                        last_event = f"Spaty znimok (vyska {sim.drone.position[2]:.1f}m, kvalita {scan_quality:.0f}%)"

                    energy_consumed = sim._calculate_energy_consumed(action)
                    motor_stress = sim._calculate_motor_stress(action)
                    sim.drone.update_health(
                        energy_consumed=energy_consumed,
                        motor_stress=motor_stress,
                        altitude=sim.drone.get_altitude(),
                        collision_occurred=False,
                        collision_damage=0,
                    )
                    sim.total_reward += sim._calculate_reward()
                    sim._record_step_data()
                    sim.step_count += 1
                else:
                    done = True
                    last_event = "Dron nie je schopny letu!"

            trail.add((int(sim.drone.position[0]), int(sim.drone.position[1])))

            render(sim.env, sim.drone, home, trail, sim.step_count, iteration, max_steps, last_event)
            time.sleep(delay)

            if not done:
                obs_after = sim._get_observation()
                done = sim._check_termination_conditions(obs_after)

    except KeyboardInterrupt:
        print("\n\n⏹  Animacia zastavena uzivatelom.\n")

    sim.drone.land()
    result = sim._calculate_episode_result()

    print("\n" + "=" * 70)
    print("VYSLEDOK LETU")
    print("=" * 70)
    print(f"Krokov:              {result['total_steps']}")
    print(f"Preskumane uzemie:   {result['exploration_ratio']*100:.1f}%")
    print(f"Spate znimky:        {result['bad_scan_count']} (nezapocitane do pokrytia)")
    print(f"Finalna baterka:     {result['final_battery']:.1f}%")
    print(f"Finalne zdravie:     {result['final_health']:.1f}%")
    print(f"Kolizie:             {len(sim.env.collision_log)}")
    tree_hits = sum(1 for c in sim.env.collision_log if c['terrain_type'] == 'tree_branches')
    print(f"  z toho o konare:   {tree_hits}")
    print(f"Finalna pozicia:     {result['final_position']}")
    if result['mission_success']:
        print(f"\n✅ MISIA USPESNA - dron sa vratil domov s dostatocnym pokrytim.")
    else:
        print(f"\n❌ MISIA NEUSPESNA - dron sa NEVRATIL domov s dostatocnym pokrytim "
              f"(bud dosla baterka/zdravie, alebo vyprsal cas).")

    return result


def main():
    parser = argparse.ArgumentParser(description="Terminalova animacia letu drona")
    parser.add_argument('--config', choices=['easy', 'medium', 'hard'], default='easy',
                        help="easy/medium/hard = config/experiments.yaml (ako main.py); "
                             "demo = zahustena ukazkova mapa z demo/demo.py s vela stromami (default)")
    parser.add_argument('--agent', choices=['adaptive', 'baseline'], default='adaptive',
                        help="ktory agent lieta (default: adaptive)")
    parser.add_argument('--speed', type=float, default=0.06,
                        help="pauza medzi krokmi v sekundach (default: 0.06)")
    parser.add_argument('--seed', type=int, default=None,
                        help="prepise seed z konfigu")
    parser.add_argument('--max-steps', type=int, default=None,
                        help="obmedzi pocet vykreslenych krokov")
    args = parser.parse_args()
        
    # Rovnaka cesta ako main.py --config easy/medium/hard:
    # ConfigLoader necita demo/demo.py, ale config/experiments.yaml.
    loader = ConfigLoader(config_dir=os.path.join(_PROJECT_ROOT, 'config'))
    config = loader.get_config(args.config)

    if args.seed is not None:
        config['episode']['seed'] = args.seed
    if args.max_steps is not None:
        config['episode']['max_steps'] = args.max_steps

    agent = AdaptiveHeightAgent() if args.agent == 'adaptive' else BoustrophedonAgent(cruise_altitude=6.0)

    animate(agent, config, delay=args.speed, max_render_steps=args.max_steps)


if __name__ == '__main__':
    main()