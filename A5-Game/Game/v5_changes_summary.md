# Scout v5

Main change: bot now figures out if its on a maze map or an open map and behaves differently.

## why

v4 was too careful in tight corridors. if the step toward gold was in the danger set it would freeze and go explore instead. but in a maze thats usually the only step available so we just lost the pot.

## new stuff

added `measure_openness()`. counts avg open neighbours per known empty tile. corridors are around 2, open areas around 6 or 7.

added two attrs in `reset()`: `map_mode` (None, "maze" or "open") and `rounds_seen`.

after round 3 we decide the map type using threshold 3.5. needs at least 12 known empty tiles, otherwise wait another round.

## new gold logic

after the sprint check:

if maze mode, take `path[0]` even if its risky. corridor usually has one way through.

if open mode, keep v4 behaviour (only step if safe).

## small stuff

bot name is "Bot5" now. cleaned up some indentation.

## things to check in batch runs

is 3.5 the right threshold
does the aggresive maze step actually help or just get us crashed more (compare v5 vs v4 on maze heavy batches)
12 tile minimum could lock in "open" too early if we happen to start in a wider spot
