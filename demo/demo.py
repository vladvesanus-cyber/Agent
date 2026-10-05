"""
Demo simulacie: porovnanie zakladneho agenta (BoustrophedonAgent - hadovy
sken bez vyuzitia vnemov) a vlastneho inteligentneho agenta
(AdaptiveHeightAgent - reaguje na percepts: lokalnu mapu, baterku,
zdravie, stromy pod sebou).

Spustenie:
    cd Project1
    python demo/demo.py

Vystup:
    demo/demo_result.png   - mapa + trajektorie + priebeh baterky/zdravia/pokrytia
    textovy report do konzoly
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch

from simulation import Simulator
from agents import AdaptiveHeightAgent, BoustrophedonAgent
from utils import set_seed


# ============================================================
# KONFIGURACIA DEMO SCENARA
# ============================================================
# Vyssi podiel stromov nez v standardnych config/*.yaml, aby sa v kratkej
# demonstracii realne prejavilo poskodenie od konarov a rozdiel v strategii
# vysky medzi oboma agentmi.
DEMO_CONFIG = {
    'map': {'width': 30, 'height': 30},
    'terrain': {
        'obstacle_ratio': 0.10,
        'tree_ratio': 0.12,
        'water_ratio': 0.03,
        'mountain_ratio': 0.02,
    },
    'drone': {
        'start_x': 15,
        'start_y': 15,
        'start_z': 0,
        'battery_capacity': 100,
        'max_altitude': 20,
    },
    'physics': {
        'energy_base_cost': 0.1,
        'altitude_multiplier': True,
        'sensor_accuracy_decline': True,
    },
    'collision': {
        'detection_enabled': True,
        'tree_collision_damage': 30,
        'obstacle_collision_damage': 100,
    },
    'observation': {
        'radius': 2,
        'include_health': True,
    },
    'episode': {
        'max_steps': 4000,
        'seed': 7,
    },
}

TERRAIN_COLORS = ['#eef5e9', '#5b4636', '#2e7d32', '#4aa3df', '#9e9e9e']
TERRAIN_LABELS = ['Volno', 'Prekazka', 'Strom', 'Voda', 'Hora']


def run(agent, label, config):
    """
    Spusti jeden epizod a vrati vysledok + zaznamenanu mapu sveta.

    Poznamka: result['episode_data']['positions'] zo simulation.py si
    neberieme - simulator do neho opakovane vklada referenciu na ten isty
    mutovany list (self.drone.position), takze po skonceni obsahuje len
    poslednu poziciu N-krat. Spravnu, uz skopirovanu historiu drzi
    Drone.position_history (tam sa pri kazdom move() uklada tuple()).
    """
    set_seed(config['episode']['seed'])
    sim = Simulator(config, agent)
    result = sim.run_episode()
    positions = list(sim.drone.position_history)
    return result, positions, sim.env.world_map.copy(), sim.env.collision_log


def coverage_curve(positions, width, height):
    """Z postupnosti navstivenych poziicii vypocita krivku % pokrytia."""
    seen = set()
    curve = []
    total = width * height
    for (x, y, z) in positions:
        seen.add((int(x), int(y)))
        curve.append(len(seen) / total * 100)
    return curve


def plot_map(ax, world_map, positions, collisions, title, home):
    cmap = ListedColormap(TERRAIN_COLORS)
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], cmap.N)
    ax.imshow(world_map, cmap=cmap, norm=norm, origin='upper')

    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    ax.plot(xs, ys, color='#d84315', linewidth=1.2, alpha=0.85, zorder=2)
    ax.scatter(xs[0], ys[0], c='black', marker='s', s=40, zorder=3, label='Start')
    ax.scatter(xs[-1], ys[-1], c='blue', marker='^', s=50, zorder=3, label='Konec')
    ax.scatter(home[0], home[1], facecolors='none', edgecolors='black',
               marker='o', s=120, linewidths=1.5, zorder=3, label='Baza')

    tree_hits = [(c['position'][0], c['position'][1]) for c in collisions
                 if c['terrain_type'] == 'tree_branches']
    other_hits = [(c['position'][0], c['position'][1]) for c in collisions
                  if c['terrain_type'] != 'tree_branches']
    if tree_hits:
        tx, ty = zip(*tree_hits)
        ax.scatter(tx, ty, marker='x', c='#b71c1c', s=70, linewidths=2,
                   zorder=4, label=f'Zrazka s konarom ({len(tree_hits)})')
    if other_hits:
        ox, oy = zip(*other_hits)
        ax.scatter(ox, oy, marker='x', c='#4e342e', s=70, linewidths=2,
                   zorder=4, label=f'Ina kolizia ({len(other_hits)})')

    ax.set_title(title, fontsize=11)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.03), fontsize=7, ncol=2, frameon=False)


def main():
    print("=" * 70)
    print("DEMO: Porovnanie zakladneho a adaptivneho agenta pri prieskume")
    print("=" * 70)

    baseline = BoustrophedonAgent(cruise_altitude=6.0)
    adaptive = AdaptiveHeightAgent()

    print("\n--- Zakladny agent (BoustrophedonAgent, hadovy sken) ---")
    base_result, base_positions, base_map, base_collisions = run(baseline, "baseline", DEMO_CONFIG)

    print("\n--- Vlastny agent (AdaptiveHeightAgent, reaguje na vnemy) ---")
    adapt_result, adapt_positions, adapt_map, adapt_collisions = run(adaptive, "adaptive", DEMO_CONFIG)

    home = (DEMO_CONFIG['drone']['start_x'], DEMO_CONFIG['drone']['start_y'])

    w, h = DEMO_CONFIG['map']['width'], DEMO_CONFIG['map']['height']
    base_cov = coverage_curve(base_positions, w, h)
    adapt_cov = coverage_curve(adapt_positions, w, h)

    # ============================================================
    # TEXTOVY REPORT
    # ============================================================
    def row(name, r, collisions):
        tree_hits = sum(1 for c in collisions if c['terrain_type'] == 'tree_branches')
        print(f"{name:<22} {r['total_steps']:>6} {r['exploration_ratio']*100:>9.1f}% "
              f"{r['final_battery']:>9.1f}% {r['final_health']:>9.1f}% "
              f"{len(collisions):>10} {tree_hits:>12}")

    print("\n" + "=" * 70)
    print("SUHRN VYSLEDKOV")
    print("=" * 70)
    print(f"{'Agent':<22} {'Kroky':>6} {'Pokrytie':>10} {'Baterka':>10} "
          f"{'Zdravie':>10} {'Kolizie':>10} {'z toho konar':>12}")
    row("Baseline (hadovy)", base_result, base_collisions)
    row("Adaptive (vlastny)", adapt_result, adapt_collisions)

    # ============================================================
    # VIZUALIZACIA
    # ============================================================
    fig = plt.figure(figsize=(13, 9))
    gs = fig.add_gridspec(2, 2, height_ratios=[2.2, 1])

    ax_map1 = fig.add_subplot(gs[0, 0])
    ax_map2 = fig.add_subplot(gs[0, 1])
    ax_curve1 = fig.add_subplot(gs[1, 0])
    ax_curve2 = fig.add_subplot(gs[1, 1])

    plot_map(ax_map1, base_map, base_positions, base_collisions,
              "Baseline: hadovy sken (bez vnemov)", home)
    plot_map(ax_map2, adapt_map, adapt_positions, adapt_collisions,
              "Adaptivny agent (rozhoduje podla vnemov)", home)

    legend_patches = [Patch(facecolor=TERRAIN_COLORS[i], label=TERRAIN_LABELS[i])
                       for i in range(len(TERRAIN_LABELS))]
    fig.legend(handles=legend_patches, loc='upper center', ncol=5,
               bbox_to_anchor=(0.5, 1.0), fontsize=8, frameon=False)

    steps_base = list(range(len(base_cov)))
    steps_adapt = list(range(len(adapt_cov)))
    ax_curve1.plot(steps_base, base_cov, color='#1565c0', label='Pokrytie (%)')
    ax_curve1.plot(steps_adapt, adapt_cov, color='#ef6c00', label='Pokrytie adaptiv. (%)')
    ax_curve1.set_title("Pokrytie uzemia v case", fontsize=10)
    ax_curve1.set_xlabel("krok")
    ax_curve1.set_ylabel("% preskumanej plochy")
    ax_curve1.legend(fontsize=8)
    ax_curve1.grid(alpha=0.3)

    ax_curve2.plot(base_result['episode_data']['energy'], color='#1565c0', label='Baterka (baseline)')
    ax_curve2.plot(adapt_result['episode_data']['energy'], color='#ef6c00', label='Baterka (adaptivny)')
    ax_curve2.plot(base_result['episode_data']['health'], color='#1565c0', linestyle='--', alpha=0.6, label='Zdravie (baseline)')
    ax_curve2.plot(adapt_result['episode_data']['health'], color='#ef6c00', linestyle='--', alpha=0.6, label='Zdravie (adaptivny)')
    ax_curve2.set_title("Baterka a zdravie v case", fontsize=10)
    ax_curve2.set_xlabel("krok")
    ax_curve2.set_ylabel("%")
    ax_curve2.legend(fontsize=7)
    ax_curve2.grid(alpha=0.3)

    fig.suptitle("Demo simulacie: prieskum uzemia dronom (seed=%d)" % DEMO_CONFIG['episode']['seed'],
                 fontsize=13, y=1.04)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'demo_result.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    print(f"\nGraf ulozeny: {out_path}")


if __name__ == '__main__':
    main()