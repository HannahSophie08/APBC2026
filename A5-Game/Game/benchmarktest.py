#!/usr/bin/env python3
"""
Benchmark scout.py against v4 and beatme-RobotRace across multiple maps.
Set QUICK_TEST = True for a fast sanity check.
"""

import random
import statistics
from pathlib import Path
from collections import Counter, defaultdict
import importlib.util

from game_utils import Map
from simulator import Simulator

# -------- base folder --------
BASE_DIR = Path(__file__).resolve().parent

# -------- config --------
QUICK_TEST = False

if QUICK_TEST:
    N_GAMES_PER_MAP = 3
    ROUNDS = 100
else:
    N_GAMES_PER_MAP = 25
    ROUNDS = 200

# -------- maps: files are in the SAME folder as this script --------
ALL_MAPS = [
    ("random", None),
    ("maze_map", BASE_DIR / "maze_map.dat"),
    ("floodfill_map", BASE_DIR / "floodfill_map.dat"),
    ("inverse_floodfill_map", BASE_DIR / "inverse_floodfill_map.dat"),
    ("random_coverage_map", BASE_DIR / "random_coverage_map.dat"),
    ("mazes_and_caves", BASE_DIR / "mazes_and_caves.dat"),
]

MAPS = [("random", None)] if QUICK_TEST else ALL_MAPS

# -------- bot files: also in same folder --------
BOT_FILES = {
    "Hannahold": BASE_DIR / "botHannah.py",
    "v6": BASE_DIR / "v6.py",
    "v5new": BASE_DIR / "scoutnew.py",
    "botHannah": BASE_DIR / "Hannah2.py",
    "group2": BASE_DIR / "group2bot.py",
}

BOT_ORDER = ["Hannahold", "v6", "v5new", "botHannah", "group2"]

# -------- checks --------
missing_bot_files = [str(f) for f in BOT_FILES.values() if not f.exists()]
missing_map_files = [str(f) for _, f in MAPS if f is not None and not f.exists()]

if missing_bot_files:
    print(f"ERROR: missing bot files: {missing_bot_files}")
    raise SystemExit(1)

if missing_map_files:
    print(f"ERROR: missing map files: {missing_map_files}")
    raise SystemExit(1)


def load_module_from_file(module_name, filepath):
    spec = importlib.util.spec_from_file_location(module_name, str(filepath))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


modules = {name: load_module_from_file(name, path) for name, path in BOT_FILES.items()}


def make_map(map_name, map_file, seed):
    if map_file is None:
        random.seed(seed)
        return Map.makeRandom(30, 30, 0.4)
    return Map.read(str(map_file))


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

        scout_games.append((finals["v5new"], map_name, map_file, seed))

        if QUICK_TEST or (game_i + 1) % 10 == 0:
            scores_str = "  ".join(f"{b}={finals[b]}" for b in BOT_ORDER)
            print(f"  game {game_i+1}/{N_GAMES_PER_MAP}: {scores_str} -> {winner}")

# -------- representative scout games --------
scout_games.sort(key=lambda t: t[0])
worst = scout_games[0]
best = scout_games[-1]
median = scout_games[len(scout_games) // 2]
replays = [("worst", worst), ("median", median), ("best", best)]

print("\n=== Replaying representative games with GIF output ===")
for label, (gold, map_name, map_file, seed) in replays:
    vizfile = BASE_DIR / f"scout_{label}_{map_name}.gif"
    print(f"  {label}: gold={gold}, map={map_name}, seed={seed} -> {vizfile.name}")
    run_game(map_name, map_file, seed, vizfile=str(vizfile))

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
            f"  {bot:8s}  wins={win_count:2d} ({win_pct:5.1f}%)  {fmt_stats(scores[bot])}"
        )
        total_wins[bot] += win_count
        total_scores[bot].extend(scores[bot])

lines.append(f"\n=== OVERALL ({len(MAPS) * N_GAMES_PER_MAP} games) ===")
total_games = len(MAPS) * N_GAMES_PER_MAP
for bot in BOT_ORDER:
    win_pct = 100 * total_wins[bot] / total_games
    lines.append(
        f"  {bot:8s}  wins={total_wins[bot]:3d} ({win_pct:5.1f}%)  {fmt_stats(total_scores[bot])}"
    )

lines.append(f"\n=== SCOUT representative games ===")
for label, (gold, map_name, _, seed) in replays:
    lines.append(f"  {label:6s}: gold={gold}, map={map_name}, seed={seed}")

output = "\n".join(lines)
print("\n" + output)

results_file = BASE_DIR / "benchmark_results.txt"
with open(results_file, "w", encoding="utf-8") as f:
    f.write(output)

print(f"\nWritten to {results_file.name}")