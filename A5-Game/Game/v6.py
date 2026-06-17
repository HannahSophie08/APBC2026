#map control having value for tiles  and avoid looping and having an idea of payoff

from collections import deque, defaultdict

from game_utils import Direction as D
from game_utils import TileStatus
from game_utils import Map
from player_base import Player


class MyPlayer(Player):

    def reset(self, player_id, max_players, width, height):
        self.player_name = "v6_frontier"
        self.player_id = player_id
        self.width = width
        self.height = height
        self.known_map = Map(width, height)
        self.visit_count = defaultdict(int)
        self.recent_positions = deque(maxlen=14)

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
        for d in D:
            dx, dy = d.as_xy()
            nx, ny = x + dx, y + dy
            if self.is_safe_tile(nx, ny, allow_unknown=True, avoid_players=False):
                degree += 1
        return degree

    def unknown_neighbors(self, x, y):
        count = 0
        for d in D:
            dx, dy = d.as_xy()
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if self.known_map[nx, ny].status == TileStatus.Unknown:
                    count += 1
        return count

    def predict_danger_tiles(self, status):
        danger = defaultdict(int)

        for other in status.others:
            if other is None:
                continue

            ox, oy = other.x, other.y
            danger[(ox, oy)] += 3

            for d in D:
                dx, dy = d.as_xy()
                nx, ny = ox + dx, oy + dy
                if self.is_safe_tile(nx, ny, allow_unknown=True, avoid_players=False):
                    danger[(nx, ny)] += 2

        return danger

    def weighted_search(self, start, target_test, status, danger_tiles):
        queue = deque([(start, [])])
        visited = {start}

        while queue:
            (cx, cy), path = queue.popleft()

            if target_test(cx, cy, path):
                return path

            candidates = []
            for d in D:
                dx, dy = d.as_xy()
                nx, ny = cx + dx, cy + dy

                if (nx, ny) in visited:
                    continue
                if not self.is_safe_tile(nx, ny, allow_unknown=True):
                    continue

                revisit = self.visit_count[(nx, ny)]
                recent = 4 if (nx, ny) in self.recent_positions else 0
                risk = 4 * danger_tiles.get((nx, ny), 0)
                choke = 3 if self.tile_degree(nx, ny) <= 1 else 0
                info_bonus = -2 * self.unknown_neighbors(nx, ny)
                candidates.append((revisit + recent + risk + choke + info_bonus, d, nx, ny))

            candidates.sort(key=lambda x: x[0])

            for _, d, nx, ny in candidates:
                visited.add((nx, ny))
                queue.append(((nx, ny), path + [d]))

        return []

    def choose_best_gold_target(self, start, status, danger_tiles):
        best_gold = None
        best_path = None
        best_score = None

        for gold_pos, amount in status.goldPots.items():
            path = self.weighted_search(
                start,
                lambda x, y, p, gp=gold_pos: (x, y) == gp,
                status,
                danger_tiles,
            )
            if gold_pos != start and not path:
                continue

            steps = len(path)
            if steps > status.goldPotRemainingRounds:
                continue

            nearby_unknown = self.unknown_neighbors(gold_pos[0], gold_pos[1])
            competition = 0
            for other in status.others:
                if other is None:
                    continue
                other_dist = max(abs(other.x - gold_pos[0]), abs(other.y - gold_pos[1]))
                if other_dist <= steps:
                    competition += 1

            score = 14 * amount - 9 * steps + 4 * nearby_unknown - 12 * competition

            if best_score is None or score > best_score:
                best_score = score
                best_gold = gold_pos
                best_path = path

        return best_gold, best_path

    def choose_frontier_path(self, start, status, danger_tiles):
        return self.weighted_search(
            start,
            lambda x, y, p: self.known_map[x, y].status == TileStatus.Unknown and len(p) > 0,
            status,
            danger_tiles,
        )

    def choose_local_move(self, status, danger_tiles):
        start = (status.x, status.y)
        options = []

        for d in D:
            dx, dy = d.as_xy()
            nx, ny = start[0] + dx, start[1] + dy

            if not self.is_safe_tile(nx, ny, allow_unknown=True):
                continue

            score = 0
            score += self.visit_count[(nx, ny)]
            score += 5 if (nx, ny) in self.recent_positions else 0
            score += 5 * danger_tiles.get((nx, ny), 0)
            score += 3 if self.tile_degree(nx, ny) <= 1 else 0
            score -= 4 * self.unknown_neighbors(nx, ny)
            if self.known_map[nx, ny].status == TileStatus.Unknown:
                score -= 3

            options.append((score, d))

        if not options:
            return []

        options.sort(key=lambda x: x[0])
        return [options[0][1]]

    def move(self, status):
        self.update_map(status)
        start = (status.x, status.y)

        self.visit_count[start] += 1
        self.recent_positions.append(start)

        danger_tiles = self.predict_danger_tiles(status)

        if status.goldPots:
            gold, path = self.choose_best_gold_target(start, status, danger_tiles)

            if gold == start:
                return []

            if path:
                steps = len(path)
                amount = status.goldPots[gold]
                sprint_cost = sum(range(1, steps + 1))

                if (
                    steps <= 3
                    and sprint_cost < status.gold
                    and amount - sprint_cost >= 15
                    and all(danger_tiles.get(self._step_pos(start, path, i), 0) == 0 for i in range(len(path)))
                ):
                    return path

                return [path[0]]

        frontier_path = self.choose_frontier_path(start, status, danger_tiles)
        if frontier_path:
            return [frontier_path[0]]

        return self.choose_local_move(status, danger_tiles)

    def _step_pos(self, start, path, i):
        x, y = start
        for step in path[: i + 1]:
            dx, dy = step.as_xy()
            x, y = x + dx, y + dy
        return (x, y)


players = [MyPlayer()]
