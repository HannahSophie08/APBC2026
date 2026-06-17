#What could be changed between scout and v4 to make it even better, different approaches so we can test 
#has gold focus but improves target score compared to beat me so also uses BFS with options when needed like sprint, penalties so only when reward is wirth it

from collections import deque, defaultdict

from game_utils import Direction as D
from game_utils import TileStatus
from game_utils import Map
from player_base import Player


class MyPlayer(Player):

    def reset(self, player_id, max_players, width, height):
        self.player_name = "v5_racer"
        self.player_id = player_id
        self.width = width
        self.height = height
        self.known_map = Map(width, height)
        self.visit_count = defaultdict(int)
        self.recent_positions = deque(maxlen=10)
        self.last_opponent_positions = {}

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

    def predict_danger_tiles(self, status):
        danger = defaultdict(int)

        visible_opponents = []
        for other in status.others:
            if other is not None:
                visible_opponents.append((other.x, other.y))

        gold_positions = list(status.goldPots.keys())

        for ox, oy in visible_opponents:
            danger[(ox, oy)] += 2

            predicted = []
            if gold_positions:
                nearest_gold = min(
                    gold_positions,
                    key=lambda g: max(abs(ox - g[0]), abs(oy - g[1]))
                )
                best_dist = max(abs(ox - nearest_gold[0]), abs(oy - nearest_gold[1]))

                for d in D:
                    dx, dy = d.as_xy()
                    nx, ny = ox + dx, oy + dy
                    if not self.is_safe_tile(nx, ny, allow_unknown=True, avoid_players=False):
                        continue
                    new_dist = max(abs(nx - nearest_gold[0]), abs(ny - nearest_gold[1]))
                    if new_dist < best_dist:
                        predicted.append((nx, ny, 3))

            if not predicted:
                for d in D:
                    dx, dy = d.as_xy()
                    nx, ny = ox + dx, oy + dy
                    if self.is_safe_tile(nx, ny, allow_unknown=True, avoid_players=False):
                        predicted.append((nx, ny, 1))

            for nx, ny, weight in predicted:
                danger[(nx, ny)] += weight

        return danger

    def bfs_path(self, start, goal, danger_tiles, allow_unknown=True):
        if start == goal:
            return []

        queue = deque([(start, [])])
        visited = {start}

        while queue:
            (cx, cy), path = queue.popleft()

            candidates = []
            for d in D:
                dx, dy = d.as_xy()
                nx, ny = cx + dx, cy + dy

                if (nx, ny) in visited:
                    continue
                if not self.is_safe_tile(nx, ny, allow_unknown=allow_unknown):
                    continue

                risk = danger_tiles.get((nx, ny), 0)
                choke = 2 if self.tile_degree(nx, ny) <= 1 else 0
                unknown_bonus = -1 if self.known_map[nx, ny].status == TileStatus.Unknown else 0
                candidates.append((risk + choke + unknown_bonus, d, nx, ny))

            candidates.sort(key=lambda x: x[0])

            for _, d, nx, ny in candidates:
                new_path = path + [d]
                if (nx, ny) == goal:
                    return new_path
                visited.add((nx, ny))
                queue.append(((nx, ny), new_path))

        return []

    def path_risk(self, start, path, danger_tiles):
        x, y = start
        risk = 0
        for d in path:
            dx, dy = d.as_xy()
            x, y = x + dx, y + dy
            risk += danger_tiles.get((x, y), 0)
            if self.tile_degree(x, y) <= 1:
                risk += 2
        return risk

    def competition_penalty(self, status, gold_pos, my_steps):
        penalty = 0
        for other in status.others:
            if other is None:
                continue
            other_dist = max(abs(other.x - gold_pos[0]), abs(other.y - gold_pos[1]))
            if other_dist < my_steps:
                penalty += 10
            elif other_dist == my_steps:
                penalty += 4
        return penalty

    def choose_gold_target(self, start, status, danger_tiles):
        best_gold = None
        best_path = None
        best_score = None

        for gold_pos, amount in status.goldPots.items():
            path = self.bfs_path(start, gold_pos, danger_tiles, allow_unknown=True)
            if gold_pos != start and not path:
                continue

            steps = len(path)
            if steps > status.goldPotRemainingRounds:
                continue

            risk = self.path_risk(start, path, danger_tiles)
            contest = self.competition_penalty(status, gold_pos, steps)
            score = 18 * amount - 11 * steps - 16 * risk - contest

            if best_score is None or score > best_score:
                best_score = score
                best_gold = gold_pos
                best_path = path

        return best_gold, best_path

    def find_frontier(self, start, danger_tiles):
        queue = deque([(start, [])])
        visited = {start}

        while queue:
            (cx, cy), path = queue.popleft()

            if self.known_map[cx, cy].status == TileStatus.Unknown and path:
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
                recent = 3 if (nx, ny) in self.recent_positions else 0
                risk = danger_tiles.get((nx, ny), 0)
                candidates.append((risk + revisit + recent, d, nx, ny))

            candidates.sort(key=lambda x: x[0])

            for _, d, nx, ny in candidates:
                visited.add((nx, ny))
                queue.append(((nx, ny), path + [d]))

        return []

    def choose_local_move(self, status, danger_tiles):
        options = []
        start = (status.x, status.y)

        for d in D:
            dx, dy = d.as_xy()
            nx, ny = start[0] + dx, start[1] + dy

            if not self.is_safe_tile(nx, ny, allow_unknown=True):
                continue

            score = 0
            score += 10 * danger_tiles.get((nx, ny), 0)
            score += self.visit_count[(nx, ny)]
            score += 4 if (nx, ny) in self.recent_positions else 0
            score += 2 if self.tile_degree(nx, ny) <= 1 else 0
            score -= 3 if self.known_map[nx, ny].status == TileStatus.Unknown else 0

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
            gold, path = self.choose_gold_target(start, status, danger_tiles)

            if gold == start:
                return []

            if path:
                steps = len(path)
                amount = status.goldPots[gold]
                sprint_cost = sum(range(1, steps + 1))
                risk = self.path_risk(start, path, danger_tiles)

                if (
                    2 <= steps <= 5
                    and sprint_cost < status.gold
                    and amount - sprint_cost >= 20
                    and risk == 0
                ):
                    return path

                return [path[0]]

        frontier = self.find_frontier(start, danger_tiles)
        if frontier:
            return [frontier[0]]

        return self.choose_local_move(status, danger_tiles)


players = [MyPlayer()]
