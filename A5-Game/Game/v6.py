#!/usr/bin/env python3

from collections import deque

from game_utils import Direction as D
from game_utils import TileStatus
from game_utils import Map
from player_base import Player


class MyPlayer(Player):

	def reset(self, player_id, max_players, width, height):
		self.player_name = "Bot6"
		self.player_id = player_id
		self.width = width
		self.height = height
		self.known_map = Map(width, height)
		self.last_opponent_positions = {}
		self.recent_positions = deque(maxlen=8)

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

	def is_walkable(self, x, y, allow_unknown=False, ignore_players=False):
		if not (0 <= x < self.width and 0 <= y < self.height):
			return False

		tile = self.known_map[x, y]

		if tile.is_blocked():
			return False

		if tile.status == TileStatus.Unknown and not allow_unknown:
			return False

		if not ignore_players and tile.obj is not None and tile.obj.is_player():
			return False

		return True

	def step_pos(self, pos, direction):
		dx, dy = direction.as_xy()
		return pos[0] + dx, pos[1] + dy

	def path_cost(self, steps):
		return steps * (steps + 1) // 2

	def chebyshev(self, a, b):
		return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

	def safe_first_step(self, start, direction, danger):
		nxt = self.step_pos(start, direction)
		return nxt not in danger

	def path_fully_known(self, start, path):
		x, y = start
		for d in path:
			x, y = self.step_pos((x, y), d)
			if not (0 <= x < self.width and 0 <= y < self.height):
				return False
			if self.known_map[x, y].status == TileStatus.Unknown:
				return False
		return True

	def max_sprint_length(self, status):
		health_ratio = status.health / status.params.maxHealth

		if health_ratio > 0.85:
			health_cap = 7
		elif health_ratio > 0.65:
			health_cap = 5
		elif health_ratio > 0.40:
			health_cap = 3
		else:
			health_cap = 1

		gold_cap = 0
		buffer = 12 if health_ratio > 0.65 else 6

		for steps in range(1, 8):
			if self.path_cost(steps) + buffer <= status.gold:
				gold_cap = steps
			else:
				break

		return min(health_cap, gold_cap)

	def predict_danger_tiles(self, status):
		danger = set()
		current_opponent_positions = {}

		for x in range(self.width):
			for y in range(self.height):
				tile = self.known_map[x, y]
				if tile.obj is None or not tile.obj.is_player():
					continue
				if tile.obj.is_player(self.player_id):
					continue

				opponent_id = tile.obj.as_player()
				current_opponent_positions[opponent_id] = (x, y)

				candidates = set()

				# Chase all visible gold pots, not just one arbitrary pot
				for gx, gy in status.goldPots.keys():
					sx = 0
					sy = 0
					if gx > x:
						sx = 1
					elif gx < x:
						sx = -1
					if gy > y:
						sy = 1
					elif gy < y:
						sy = -1

					nx, ny = x + sx, y + sy
					if 0 <= nx < self.width and 0 <= ny < self.height:
						if not self.known_map[nx, ny].is_blocked():
							candidates.add((nx, ny))

				# Continue previous direction as fallback
				if not candidates and opponent_id in self.last_opponent_positions:
					lx, ly = self.last_opponent_positions[opponent_id]
					dx = x - lx
					dy = y - ly
					nx, ny = x + dx, y + dy
					if 0 <= nx < self.width and 0 <= ny < self.height:
						if not self.known_map[nx, ny].is_blocked():
							candidates.add((nx, ny))

				# Adjacent area also risky in cramped fights
				for cx, cy in candidates:
					danger.add((cx, cy))
					for d in D:
						ax, ay = self.step_pos((cx, cy), d)
						if 0 <= ax < self.width and 0 <= ay < self.height:
							if not self.known_map[ax, ay].is_blocked():
								danger.add((ax, ay))

		self.last_opponent_positions = current_opponent_positions
		return danger

	def bfs_path(self, start, goal, allow_unknown=True, danger=None):
		if danger is None:
			danger = set()

		if start == goal:
			return []

		q = deque([start])
		parent = {start: None}
		move_used = {}

		while q:
			cur = q.popleft()

			for d in D:
				nxt = self.step_pos(cur, d)
				if nxt in parent:
					continue
				if nxt in danger:
					continue
				if not self.is_walkable(nxt[0], nxt[1], allow_unknown=allow_unknown):
					continue

				parent[nxt] = cur
				move_used[nxt] = d

				if nxt == goal:
					path = []
					node = nxt
					while parent[node] is not None:
						path.append(move_used[node])
						node = parent[node]
					path.reverse()
					return path

				q.append(nxt)

		return []

	def bfs_distances(self, start, allow_unknown=True):
		q = deque([start])
		dist = {start: 0}

		while q:
			cur = q.popleft()
			for d in D:
				nxt = self.step_pos(cur, d)
				if nxt in dist:
					continue
				if not self.is_walkable(nxt[0], nxt[1], allow_unknown=allow_unknown):
					continue
				dist[nxt] = dist[cur] + 1
				q.append(nxt)

		return dist

	def opponent_pressure(self, status, gold_pos, my_steps):
		best_opp = None

		for other in status.others:
			if other is None:
				continue
			opp_steps = self.chebyshev((other.x, other.y), gold_pos)
			if best_opp is None or opp_steps < best_opp:
				best_opp = opp_steps

		if best_opp is None:
			return 0

		if best_opp < my_steps:
			return 35
		if best_opp == my_steps:
			return 18
		if best_opp == my_steps + 1:
			return 8
		return 0

	def gold_score(self, status, start, gold_pos, amount, path, danger):
		steps = len(path)

		if steps > status.goldPotRemainingRounds:
			return None

		cost = self.path_cost(steps)
		if cost > status.gold:
			return None

		net = amount - cost
		if net < -5:
			return None

		score = 0.0
		score += 4.0 * amount
		score -= 2.2 * cost
		score -= 7.0 * steps
		score -= self.opponent_pressure(status, gold_pos, steps)

		if steps <= 2:
			score += 10

		if steps <= status.goldPotRemainingRounds - 2:
			score += 6

		if path and self.safe_first_step(start, path[0], danger):
			score += 8
		elif path:
			score -= 20

		if self.path_fully_known(start, path):
			score += 6
		else:
			score -= 4

		return score

	def choose_gold_target(self, status, start, danger):
		best = None

		for gold_pos, amount in status.goldPots.items():
			path = self.bfs_path(start, gold_pos, allow_unknown=True, danger=danger)

			if not path and gold_pos != start:
				path = self.bfs_path(start, gold_pos, allow_unknown=True, danger=set())

			if not path and gold_pos != start:
				continue

			score = self.gold_score(status, start, gold_pos, amount, path, danger)
			if score is None:
				continue

			item = (score, -len(path), amount, gold_pos, path)
			if best is None or item > best:
				best = item

		if best is None:
			return None, None, None

		return best[3], best[4], best[0]

	def choose_positioning_move(self, status, start, danger):
		legal = []
		for d in D:
			nx, ny = self.step_pos(start, d)
			if not self.is_walkable(nx, ny, allow_unknown=True):
				continue
			legal.append(d)

		if not legal:
			return []

		visible_gold = list(status.goldPots.keys())

		def tile_value(pos):
			x, y = pos
			value = 0.0

			# Prefer central control slightly
			cx = (self.width - 1) / 2.0
			cy = (self.height - 1) / 2.0
			value -= 0.15 * (abs(x - cx) + abs(y - cy))

			# Prefer not to step into danger
			if pos in danger:
				value -= 20

			# Avoid ping-pong movement
			if pos in self.recent_positions:
				value -= 6

			# Slight preference for unknowns, but not random wandering
			if self.known_map[x, y].status == TileStatus.Unknown:
				value += 2
			else:
				value += 1

			# If gold is visible, move to reduce average distance to all pots
			if visible_gold:
				total = 0
				for gp in visible_gold:
					total += self.chebyshev(pos, gp)
				value -= 1.3 * (total / len(visible_gold))

				# Stronger reward for getting closer to the single best-value gold region
				nearest = min(self.chebyshev(pos, gp) for gp in visible_gold)
				value -= 1.8 * nearest

			return value

		best_dir = None
		best_score = None

		for d in legal:
			nxt = self.step_pos(start, d)
			score = tile_value(nxt)

			if best_score is None or score > best_score:
				best_score = score
				best_dir = d

		if best_dir is None or best_score < -50:
			return []

		return [best_dir]

	def choose_action(self, status, start, danger):
		gold_pos, path, gold_score = self.choose_gold_target(status, start, danger)

		if gold_pos is not None and path is not None:
			steps = len(path)
			cost = self.path_cost(steps)
			net = status.goldPots[gold_pos] - cost

			# Take gold by walking one step
			if path and self.safe_first_step(start, path[0], danger):
				# Sprint only when clearly profitable, affordable, and safe
				if (steps >= 2 and
					steps <= self.max_sprint_length(status) and
					net >= 18 and
					self.path_fully_known(start, path) and
					status.goldPotRemainingRounds >= steps):
					return path
				return [path[0]]

			# If target is strong but first step risky, try normal one-step path ignoring danger
			if path:
				return [path[0]]

		# No worthwhile gold -> reposition instead of freezing
		return self.choose_positioning_move(status, start, danger)

	def move(self, status):
		self.update_map(status)
		start = (status.x, status.y)
		self.recent_positions.append(start)

		danger = self.predict_danger_tiles(status)
		move = self.choose_action(status, start, danger)

		if move:
			return move
		return []


players = [MyPlayer()]
