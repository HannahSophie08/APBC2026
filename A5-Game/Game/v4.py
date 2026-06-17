# NEW: estimate how dangerous each tile is based on visible opponent positions
# and likely next moves, so we do not walk into likely collisions.

# NEW: count how many safe exits a tile has.
# Tiles with very few exits are more dangerous on dense maps because
# they are easier to block and harder to escape from.

# CHANGED: gold selection is no longer based only on shortest path.
# We now also consider:
# - gold amount
# - path risk
# - whether other players are likely to reach it too
# - whether the pot might expire before arrival

# CHANGED: BFS still finds paths, but we now prefer safer neighboring tiles first.
# This keeps the algorithm simple while making it more tactical.

# CHANGED: exploration is now a fallback that also avoids danger tiles
# and repeated oscillation, instead of only preferring unknown tiles.
#!/usr/bin/env python3
from collections import deque, defaultdict

from game_utils import Direction as D
from game_utils import TileStatus
from game_utils import Map
from player_base import Player


class MyPlayer(Player):

    def reset(self, player_id, max_players, width, height):
        self.player_name = "v4"
        self.player_id = player_id
        self.width = width
        self.height = height
        self.known_map = Map(width, height)
        self.visit_count = {}
        self.recent_positions = deque(maxlen=12)
        self.last_seen_positions = {}

    def round_begin(self, r):
        pass

    def set_mines(self, status):
        return []

    def update_map(self, status):
        for x in range(self.width):
            for y in range(self.height):
                self.known_map[x, y].obj = None

        for x in range(status.map.width):
            for y in range(status.map.height):
                tile = status.map[x, y]
                if tile.status != TileStatus.Unknown:
                    self.known_map[x, y].status = tile.status
                    self.known_map[x, y].obj = tile.obj

    def is_safe_tile(self, x, y, allow_unknown=False, avoid_players=True):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False

        tile = self.known_map[x, y]

        if tile.is_blocked():
            return False

        if tile.status == TileStatus.Unknown and not allow_unknown:
            return False

        if avoid_players and tile.obj is not None and tile.obj.is_player():
            return False

        return True

    def tile_degree(self, x, y):
        degree = 0
        for direction in D:
            dx, dy = direction.as_xy()
            nx, ny = x + dx, y + dy
            if self.is_safe_tile(nx, ny, allow_unknown=True, avoid_players=False):
                degree += 1
        return degree

    def predict_danger_tiles(self, status):
        danger = defaultdict(int)

        for other in status.others:
            if other is None:
                continue

            other_pos = (other.x, other.y)

            likely_moves = []

            if status.goldPots:
                nearest_gold = min(
                    status.goldPots.keys(),
                    key=lambda g: max(abs(other.x - g[0]), abs(other.y - g[1]))
                )

                best_dist = max(abs(other.x - nearest_gold[0]), abs(other.y - nearest_gold[1]))

                for direction in D:
                    dx, dy = direction.as_xy()
                    nx, ny = other.x + dx, other.y + dy
                    if not self.is_safe_tile(nx, ny, allow_unknown=True, avoid_players=False):
                        continue
                    new_dist = max(abs(nx - nearest_gold[0]), abs(ny - nearest_gold[1]))
                    if new_dist < best_dist:
                        likely_moves.append((nx, ny, 3))

            if not likely_moves:
                for direction in D:
                    dx, dy = direction.as_xy()
                    nx, ny = other.x + dx, other.y + dy
                    if self.is_safe_tile(nx, ny, allow_unknown=True, avoid_players=False):
                        likely_moves.append((nx, ny, 1))

            danger[other_pos] += 1
            for nx, ny, weight in likely_moves:
                danger[(nx, ny)] += weight

        return danger

    def breadth_first_search(self, start, goal, danger_tiles=None, allow_unknown=True):
        if start == goal:
            return []

        if danger_tiles is None:
            danger_tiles = {}

        queue = deque()
        queue.append((start, []))
        visited = {start}

        while queue:
            (cx, cy), path = queue.popleft()

            candidates = []
            for direction in D:
                dx, dy = direction.as_xy()
                nx, ny = cx + dx, cy + dy

                if (nx, ny) in visited:
                    continue
                if not self.is_safe_tile(nx, ny, allow_unknown=allow_unknown):
                    continue

                risk = danger_tiles.get((nx, ny), 0)
                degree_penalty = 2 if self.tile_degree(nx, ny) <= 2 else 0
                candidates.append((risk + degree_penalty, direction, nx, ny))

            candidates.sort(key=lambda item: item[0])

            for _, direction, nx, ny in candidates:
                new_path = path + [direction]
                if (nx, ny) == goal:
                    return new_path
                visited.add((nx, ny))
                queue.append(((nx, ny), new_path))

        return []

    def estimate_path_risk(self, start, path, danger_tiles):
        x, y = start
        risk = 0
        for step in path:
            dx, dy = step.as_xy()
            x, y = x + dx, y + dy
            risk += danger_tiles.get((x, y), 0)
            if self.tile_degree(x, y) <= 2:
                risk += 2
        return risk

    def competition_penalty(self, status, gold_pos, my_steps):
        penalty = 0
        for other in status.others:
            if other is None:
                continue
            other_dist = max(abs(other.x - gold_pos[0]), abs(other.y - gold_pos[1]))
            if other_dist < my_steps:
                penalty += 3
            elif other_dist == my_steps:
                penalty += 1
        return penalty

    def choose_best_gold_target(self, start, status, danger_tiles):
        best_gold = None
        best_path = None
        best_score = None

        for gold_pos, amount in status.goldPots.items():
            path = self.breadth_first_search(start, gold_pos, danger_tiles, allow_unknown=True)
            if not path and gold_pos != start:
                continue

            steps = len(path)
            if steps > status.goldPotRemainingRounds:
                continue

            path_risk = self.estimate_path_risk(start, path, danger_tiles)
            contest = self.competition_penalty(status, gold_pos, steps)
            expiry_risk = max(0, steps - status.goldPotRemainingRounds + 1)

            score = amount - 8 * steps - 15 * path_risk - 12 * contest - 50 * expiry_risk

            if best_score is None or score > best_score:
                best_score = score
                best_gold = gold_pos
                best_path = path

        return best_gold, best_path

    def find_nearest_unknown(self, start, danger_tiles):
        queue = deque()
        queue.append((start, []))
        visited = {start}

        while queue:
            (cx, cy), path = queue.popleft()

            if self.known_map[cx, cy].status == TileStatus.Unknown and path:
                return path

            candidates = []
            for direction in D:
                dx, dy = direction.as_xy()
                nx, ny = cx + dx, cy + dy

                if (nx, ny) in visited:
                    continue
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                if not self.is_safe_tile(nx, ny, allow_unknown=True):
                    continue

                risk = danger_tiles.get((nx, ny), 0)
                revisit = self.visit_count.get((nx, ny), 0)
                recent = 4 if (nx, ny) in self.recent_positions else 0
                candidates.append((risk + revisit + recent, direction, nx, ny))

            candidates.sort(key=lambda item: item[0])

            for _, direction, nx, ny in candidates:
                visited.add((nx, ny))
                queue.append(((nx, ny), path + [direction]))

        return []

    def choose_exploration_move(self, status, danger_tiles):
        options = []

        for direction in D:
            dx, dy = direction.as_xy()
            nx, ny = status.x + dx, status.y + dy

            if not self.is_safe_tile(nx, ny, allow_unknown=True):
                continue

            visit_penalty = self.visit_count.get((nx, ny), 0)
            recent_penalty = 5 if (nx, ny) in self.recent_positions else 0
            unknown_bonus = -3 if self.known_map[nx, ny].status == TileStatus.Unknown else 0
            danger_penalty = 10 * danger_tiles.get((nx, ny), 0)
            choke_penalty = 3 if self.tile_degree(nx, ny) <= 2 else 0

            score = visit_penalty + recent_penalty + unknown_bonus + danger_penalty + choke_penalty
            options.append((score, direction))

        if not options:
            return []

        options.sort(key=lambda item: item[0])
        return [options[0][1]]

    def move(self, status):
        self.update_map(status)
        start = (status.x, status.y)

        self.visit_count[start] = min(self.visit_count.get(start, 0) + 1, 3)
        self.recent_positions.append(start)

        danger_tiles = self.predict_danger_tiles(status)

        if status.goldPots:
            gold, path = self.choose_best_gold_target(start, status, danger_tiles)

            if gold == start:
                return []

            if path:
                steps = len(path)
                gold_amount = status.goldPots[gold]
                sprint_cost = sum(range(1, steps + 1))
                path_risk = self.estimate_path_risk(start, path, danger_tiles)

                if (
                    steps <= 4
                    and sprint_cost < status.gold
                    and gold_amount - sprint_cost > 25
                    and path_risk == 0
                ):
                    return path

                return [path[0]]

        explore_path = self.find_nearest_unknown(start, danger_tiles)
        if explore_path:
            return [explore_path[0]]

        return self.choose_exploration_move(status, danger_tiles)


players = [MyPlayer()]