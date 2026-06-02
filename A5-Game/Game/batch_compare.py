#!/usr/bin/env python3
"""
Benchmark scout.py against v2, v3, and silly across multiple maps.
Set QUICK_TEST = True for a fast sanity check (3 games, 1 map).
"""

import importlib
import os
import random
import statistics
from collections import Counter, defaultdict
from game_utils import Map
from simulator import Simulator

# -------- config --------
QUICK_TEST = False   # <-- flip to False for full 50-games-per-map run

if QUICK_TEST:
    N_GAMES_PER_MAP = 3
    ROUNDS = 100
else:
    N_GAMES_PER_MAP = 25
    ROUNDS = 200

# which maps to test. ("random", None) generates a new random map each game.
ALL_MAPS = [
    ("random",                None),
    ("maze_map",              "maps/maze_map.dat"),
    ("floodfill_map",         "maps/floodfill_map.dat"),
    ("inverse_floodfill_map", "maps/inverse_floodfill_map.dat"),
    ("random_coverage_map",   "maps/random_coverage_map.dat"),
    ("mazes_and_caves",       "maps/mazes_and_caves.dat"),
]

# in quick test, only use random map (no file dependency)
MAPS = [("random", None)] if QUICK_TEST else ALL_MAPS

BOT_MODULES = {
    "v2":    "v2",
    "v3":    "v3",
    "scout": "scout",
    "silly": "beatme-RobotRace",
}
BOT_ORDER = ["v2", "v3", "scout", "silly"]

# -------- check map files exist before starting --------
missing = [f for _, f in MAPS if f is not None and not os.path.exists(f)]
if missing:
    print(f"ERROR: missing map files: {missing}")
    print("Either copy them into this folder or remove them from MAPS.")
    exit(1)

# -------- import bot modules --------
modules = {name: importlib.import_module(mod) for name, mod in BOT_MODULES.items()}


def make_map(map_name, map_file, seed):
    if map_file is None:
        random.seed(seed)
        return Map.makeRandom(30, 30, 0.4)
    return Map.read(map_file)


def run_game(map_name, map_file, seed, vizfile=None):
    m = make_map(map_name, map_file, seed)
    sim = Simulator(map=m, vizfile=vizfile, framerate=8)
    sim.printInitial = False
    sim.printEvents = False
    sim.printMoves = False
    sim.printRoundBegin = False

    for name in BOT_ORDER:
        p = modules[name].players[0].__class__()
        p.player_modname = name
        sim.add_player(p)

    sim.play(rounds=ROUNDS, jumps_allowed=False, mine_mode="wall")

    return {name: sim._status[i].gold for i, name in enumerate(BOT_ORDER)}


# -------- run games --------
per_map_scores = defaultdict(lambda: defaultdict(list))
per_map_wins = defaultdict(Counter)
scout_games = []

for map_name, map_file in MAPS:
    print(f"\n=== Map: {map_name} ===")
    for game_i in range(N_GAMES_PER_MAP):
        seed = hash((map_name, game_i)) & 0xFFFFFFFF
        finals = run_game(map_name, map_file, seed)

        winner = max(finals, key=finals.get)
        per_map_wins[map_name][winner] += 1
        for bot, g in finals.items():
            per_map_scores[map_name][bot].append(g)

        scout_games.append((finals["scout"], map_name, map_file, seed))

        if QUICK_TEST or (game_i + 1) % 10 == 0:
            scores_str = "  ".join(f"{b}={finals[b]}" for b in BOT_ORDER)
            print(f"  game {game_i+1}/{N_GAMES_PER_MAP}: {scores_str} -> {winner}")

# -------- find scout best/median/worst --------
scout_games.sort(key=lambda t: t[0])
worst = scout_games[0]
best = scout_games[-1]
median = scout_games[len(scout_games) // 2]
replays = [("worst", worst), ("median", median), ("best", best)]

print("\n=== Replaying representative games with GIF output ===")
for label, (gold, map_name, map_file, seed) in replays:
    vizfile = f"scout_{label}_{map_name}.gif"
    print(f"  {label}: gold={gold}, map={map_name}, seed={seed} -> {vizfile}")
    run_game(map_name, map_file, seed, vizfile=vizfile)


# -------- stats --------
def fmt_stats(scores):
    if not scores:
        return "no data"
    return (
        f"mean={statistics.mean(scores):6.1f}  "
        f"median={statistics.median(scores):6.1f}  "
        f"stdev={statistics.stdev(scores) if len(scores) > 1 else 0:5.1f}  "
        f"min={min(scores):4d}  max={max(scores):4d}"
    )


lines = []
lines.append(f"Benchmark results (QUICK_TEST={QUICK_TEST})")
lines.append(f"N_GAMES_PER_MAP = {N_GAMES_PER_MAP}, ROUNDS = {ROUNDS}")
lines.append("=" * 80)

total_wins = Counter()
total_scores = defaultdict(list)

for map_name, _ in MAPS:
    lines.append(f"\n--- {map_name} ---")
    wins = per_map_wins[map_name]
    scores = per_map_scores[map_name]
    for bot in BOT_ORDER:
        win_count = wins[bot]
        win_pct = 100 * win_count / N_GAMES_PER_MAP
        lines.append(
            f"  {bot:6s}  wins={win_count:2d} ({win_pct:5.1f}%)  {fmt_stats(scores[bot])}"
        )
        total_wins[bot] += win_count
        total_scores[bot].extend(scores[bot])

lines.append(f"\n=== OVERALL ({len(MAPS) * N_GAMES_PER_MAP} games) ===")
total_games = len(MAPS) * N_GAMES_PER_MAP
for bot in BOT_ORDER:
    win_pct = 100 * total_wins[bot] / total_games
    lines.append(
        f"  {bot:6s}  wins={total_wins[bot]:3d} ({win_pct:5.1f}%)  {fmt_stats(total_scores[bot])}"
    )

lines.append(f"\n=== SCOUT representative games ===")
for label, (gold, map_name, _, seed) in replays:
    lines.append(f"  {label:6s}: gold={gold}, map={map_name}, seed={seed}")

output = "\n".join(lines)
print("\n" + output)

with open("benchmark_results.txt", "w") as f:
    f.write(output)

print("\nWritten to benchmark_results.txt")