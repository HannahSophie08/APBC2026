#!/usr/bin/env python3
"""
Benchmark scout against v2, v3, v4, v5 and silly across all maps.
Speed-only: no GIFs, no viz, just runs everything in parallel and prints stats.
Set QUICK_TEST = True for a fast sanity check (3 games, random map only).
"""

import importlib
import os
import random
import statistics
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

from game_utils import Map
from simulator import Simulator

# -------- config --------
QUICK_TEST = False   # <-- flip to True for a quick sanity check

if QUICK_TEST:
    N_GAMES_PER_MAP = 3
    ROUNDS = 100
else:
    N_GAMES_PER_MAP = 25
    ROUNDS = 200

# how many games to run at once. None = use all cores.
# drop to e.g. 4 if your laptop gets too hot / unresponsive
MAX_WORKERS = None

ALL_MAPS = [
    ("random",                None),
    ("maze_map",              "maps/maze_map.dat"),
    ("floodfill_map",         "maps/floodfill_map.dat"),
    ("inverse_floodfill_map", "maps/inverse_floodfill_map.dat"),
    ("random_coverage_map",   "maps/random_coverage_map.dat"),
    ("mazes_and_caves",       "maps/mazes_and_caves.dat"),
]

MAPS = [("random", None)] if QUICK_TEST else ALL_MAPS

BOT_MODULES = {
    "Test": "test-RobotRace",
    "Beatme": "beatme-RobotRace",
    "Scout-version 2": "v2",
    "Scout-version 3": "v3",
    "Scout-version 4": "scout_v4",
    "Scout-version 5": "scout_v5",
}

BOT_ORDER = ["Test", "Beatme", "Scout-version 2", "Scout-version 3", "Scout-version 4", "Scout-version 5"]

# -------- import bot modules (runs in every worker too) --------
modules = {name: importlib.import_module(mod) for name, mod in BOT_MODULES.items()}


def make_map(map_name, map_file, seed):
    if map_file is None:
        random.seed(seed)
        return Map.makeRandom(30, 30, 0.4)
    return Map.read(map_file)


def run_game(map_name, map_file, seed):
    m = make_map(map_name, map_file, seed)
    # vizfile=None -> no rendering, nothing drawn
    sim = Simulator(map=m, vizfile=None, framerate=10)
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


# one job = one game. top level so workers can pickle it.
def run_one(job):
    map_name, map_file, seed = job
    return map_name, seed, run_game(map_name, map_file, seed)


def fmt_stats(scores):
    if not scores:
        return "no data"
    return (
        f"mean={statistics.mean(scores):6.1f}  "
        f"median={statistics.median(scores):6.1f}  "
        f"stdev={statistics.stdev(scores) if len(scores) > 1 else 0:5.1f}  "
        f"min={min(scores):4d}  max={max(scores):4d}"
    )


def main():
    missing = [f for _, f in MAPS if f is not None and not os.path.exists(f)]
    if missing:
        print(f"ERROR: missing map files: {missing}")
        print("Either copy them into a maps/ folder or fix the paths in ALL_MAPS.")
        return

    # build every game up front, seeds set here so they stay stable across runs
    jobs = []
    for map_name, map_file in MAPS:
        for game_i in range(N_GAMES_PER_MAP):
            seed = hash((map_name, game_i)) & 0xFFFFFFFF
            jobs.append((map_name, map_file, seed))

    total_games = len(jobs)
    print(f"Running {total_games} games in parallel...")

    per_map_scores = defaultdict(lambda: defaultdict(list))
    per_map_wins = defaultdict(Counter)

    start_time = time.time()
    done = 0
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for map_name, seed, finals in ex.map(run_one, jobs):
            winner = max(finals, key=finals.get)
            per_map_wins[map_name][winner] += 1
            for bot, g in finals.items():
                per_map_scores[map_name][bot].append(g)

            done += 1
            if done % 10 == 0 or done == total_games:
                print(f"  {done}/{total_games} games done")

    elapsed = time.time() - start_time

    # -------- stats --------
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

    lines.append(f"\n=== OVERALL ({total_games} games) ===")
    for bot in BOT_ORDER:
        win_pct = 100 * total_wins[bot] / total_games
        lines.append(
            f"  {bot:6s}  wins={total_wins[bot]:3d} ({win_pct:5.1f}%)  {fmt_stats(total_scores[bot])}"
        )

    lines.append(f"\nTotal runtime: {elapsed:.1f}s")

    output = "\n".join(lines)
    print("\n" + output)

    with open("benchmark_results.txt", "w") as f:
        f.write(output)

    print("\nWritten to benchmark_results.txt")


# required for parallel runs on Windows
if __name__ == "__main__":
    main()