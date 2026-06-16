# Bot4 v3 — Changes Compared to v2

**Author:** [your name]
**Date:** Before milestone 1 meeting
**File:** `scout.py`

## Summary

Naja's v2 was already a working BFS-based bot with map memory and exploration scoring. My v3 keeps all of v2's exploration logic and adds three game-relevant features (player avoidance, pot-expiry handling, sprinting), plus one small tuning fix to a v2 feature.

In a 20-game benchmark batch run six times against v2 and SillyScout, v3 won the batch five out of six runs.


## What I changed

### 1. Player collision avoidance *(new)*

v2's BFS only treats walls as blocked. If another bot is standing on a tile, v2 would happily plan a path through it and crash. I added `is_safe_tile()` as a helper that also blocks tiles with visible players, and updated `update_map()` to track player and gold objects (not just terrain) so the check has the data it needs.

**Why:** crashes cost 15–20 HP. Avoiding even one crash per game saves a round of healing time.

**Caveat:** this only avoids *currently visible* players. If a player moves into our target tile between rounds, we can still crash. The `(FIX!)` comment in the code flags this as known and not fully solved.


### 2. Pot-expiry check *(new)*

If the path to a gold pot is longer than the rounds the pot has remaining (`status.goldPotRemainingRounds`), v2 would still chase it and arrive after the pot disappeared, wasting moves and gold. In v3, when this happens, we explore toward an unknown tile instead.

**Why:** every action costs gold (1, 3, 6, 10, ... for k moves). Spending those on a pot that will vanish is pure loss. Better to position ourselves for the next pot.


### 3. Sprint logic *(new)*

v2 always returns `[path[0]]` — exactly one step per round. v3 returns multiple steps when:

- The gold is within 5 steps
- We can afford the cost (`cost < status.gold`)
- The net gain after action costs is greater than 30 gold
- We appear to be the closest visible player to the pot (`am_i_closest`)

Cost for k actions is k(k+1)/2 — so 5 steps cost 15 gold. A pot of 100+ minus 15 is still a strong win, and we arrive 4 rounds earlier than v2 would.

**Why:** SillyScout never sprints. Any time we successfully sprint to a pot, we beat both v2 and SillyScout to it. This is our main competitive edge over both opponents.


### 4. `find_nearest_unknown()` helper *(new)*

A dedicated BFS that finds the closest unknown tile and returns a path toward it. Used as a fallback in two places: when the pot will expire before we arrive, and when there's no gold pot at all. v2 just falls back to single-step scored exploration in both cases.

**Why:** picks a coherent direction toward genuinely new map area rather than choosing tile-by-tile, which can get stuck oscillating between low-score directions.


### 5. `allow_unknown` flag on `is_safe_tile` *(new)*

`is_safe_tile` takes an optional `allow_unknown` parameter. Default is False (strict), but BFS and exploration both pass `allow_unknown=True` so the bot can plan paths through fog of war — matching v2's willingness to walk through unknown tiles.

**Why:** without this, an earlier iteration of v3 refused to path through unknowns and got badly stuck. This was a regression we caught in benchmarking and fixed. With the fix, v3 chases gold as aggressively as v2 does.


### 6. `visit_count` capped at 3 *(tuning of Naja's feature)*

v2's `visit_count` grows without bound — a tile visited 50 times gets a penalty of 50. Over long games this creates an irrational aversion to familiar areas, even when those areas are on the best route to gold. Capping at 3 keeps the "prefer somewhere new" behavior for the first few visits but stops accumulating after that.

**Why:** in benchmarking, v3's avg gold improved noticeably after this change. The bot stops avoiding its own neighborhood as the game progresses.


### 7. `set_mines()` returning `[]` *(housekeeping)*

The simulator calls `set_mines()` every round. v2 doesn't define it, which would raise `NotImplementedError`. I added a stub that returns an empty list (we don't place mines yet).


## What I kept from v2 unchanged

Most of the bot is still Naja's design:

- BFS pathfinding algorithm
- Multi-pot target selection in `choose_best_gold_target` (shortest path, ties broken by gold amount)
- Exploration scoring weights: `visit_count`, `recent_positions` (12-deep deque), `unknown_bonus = -3`
- Overall structure of `move()` — gold first, exploration as fallback
- Map tracking via `known_map`


## Benchmark results

Three-way batches of 20 games each (v2 vs v3 vs SillyScout), run six times:

- v3 won the batch (most total wins) in 5 of 6 runs
- v2 also beats SillyScout in win count on its own, so v3 inherits that competitiveness
- After fixing the unknown-tile regression, v3 sits clearly ahead of v2

Per-batch numbers vary because the simulator generates a different random map per game. Aggregate trend is consistent.


## Known issues / next steps

Things I'd want to look at after milestone 1:

- **Predicted player positions.** Current player avoidance only blocks tiles where we *currently see* another player. We can still crash if they move into our target tile. A one-round lookahead would catch most of these.
- **Mine setting.** Currently we set no mines. Could be a useful offensive tool against SillyScout, which doesn't avoid mine fields in any special way.
- **Multi-pot games.** Our target selection handles them, but the game usually only has one pot at a time, so this is untested in practice.
- **Cleanup.** A few leftover comments and an unused `import random` at the top — non-blocking, but worth tidying.
