#!/usr/bin/env python3

from collections import deque

from game_utils import Direction as D
from game_utils import TileStatus
from game_utils import Map
from player_base import Player


class MyPlayer(Player):

	def reset(self, player_id, max_players, width, height):
		self.player_name = "Bot5_gold_only_v2"
		self.player_id = player_id
		self.width = width
		self.height = height
		self.known_map = Map(width, height)
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

	def is_safe_tile(self, x, y, allow_unknown=False):
		if not (0 <= x < self.width and 0 <= y < self.height):
			return False

		tile = self.known_map[x, y]

		if tile.is_blocked():
			return False

		if tile.status == TileStatus.Unknown and not allow_unknown:
			return False

		if tile.obj is not None and tile.obj.is_player():
			return False

		return True

	def path_cost(self, steps):
		return sum(range(1, steps + 1))

	def safe_first_step(self, start, direction, danger):
		dx, dy = direction.as_xy()
		return (start[0] + dx, start[1] + dy) not in danger

	def opponent_distance_to_gold(self, status, gold_pos):
		best = None
		gx, gy = gold_pos

		for other in status.others:
			if other is None:
				continue
			dist = max(abs(other.x - gx), abs(other.y - gy))
			if best is None or dist < best:
				best = dist

		return best

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
				opponent_position = (x, y)
				current_opponent_positions[opponent_id] = opponent_position

				candidate_tiles = set()

				# Predict movement toward every visible gold pot, not just one arbitrary pot
				for gold_x, gold_y in status.goldPots.keys():
					step_x = 0
					step_y = 0

					if gold_x > x:
						step_x = 1
					elif gold_x < x:
						step_x = -1

					if gold_y > y:
						step_y = 1
					elif gold_y < y:
						step_y = -1

					next_x = x + step_x
					next_y = y + step_y

					if 0 <= next_x < self.width and 0 <= next_y < self.height:
						if not self.known_map[next_x, next_y].is_blocked():
							candidate_tiles.add((next_x, next_y))

				# Fallback: continue previous direction if no gold-based prediction exists
				if not candidate_tiles and opponent_id in self.last_opponent_positions:
					last_x, last_y = self.last_opponent_positions[opponent_id]
					move_x = x - last_x
					move_y = y - last_y
					next_x = x + move_x
					next_y = y + move_y

					if 0 <= next_x < self.width and 0 <= next_y < self.height:
						if not self.known_map[next_x, next_y].is_blocked():
							candidate_tiles.add((next_x, next_y))

				danger.update(candidate_tiles)

		self.last_opponent_positions = current_opponent_positions
		return danger

	def breadth_first_search(self, start, goal, danger=None):
		if danger is None:
			danger = set()

		if start == goal:
			return []

		queue = deque()
		queue.append((start, []))
		visited = {start}

		while queue:
			(cx, cy), path = queue.popleft()

			for direction in D:
				dx, dy = direction.as_xy()
				nx, ny = cx + dx, cy + dy

				if (nx, ny) in visited:
					continue
				if (nx, ny) in danger:
					continue
				if not self.is_safe_tile(nx, ny, allow_unknown=True):
					continue

				new_path = path + [direction]

				if (nx, ny) == goal:
					return new_path

				visited.add((nx, ny))
				queue.append(((nx, ny), new_path))

		return []

	def choose_best_gold_target(self, start, status, danger):
		best_gold = None
		best_path = None
		best_score = None

		my_x, my_y = start

		for gold_pos, amount in status.goldPots.items():
			path = self.breadth_first_search(start, gold_pos, danger)

			if not path and gold_pos != start:
				continue

			steps = len(path)

			if steps > status.goldPotRemainingRounds:
				continue

			cost = self.path_cost(steps)
			net_profit = amount - cost

			if cost > status.gold:
				continue

			my_dist = max(abs(my_x - gold_pos[0]), abs(my_y - gold_pos[1]))
			opp_dist = self.opponent_distance_to_gold(status, gold_pos)

			first_step_risky = 1
			if path:
				first_step_risky = 0 if self.safe_first_step(start, path[0], danger) else 1
			else:
				first_step_risky = 0

			# Higher net profit is better.
			# Tie-breakers:
			# 1) safer first step
			# 2) shorter path
			# 3) if opponents are competing, prefer pots where we are relatively closer
			# 4) larger raw amount
			relative_race = 999
			if opp_dist is not None:
				relative_race = my_dist - opp_dist

			score = (
				-net_profit,
				first_step_risky,
				steps,
				relative_race,
				-amount
			)

			if best_score is None or score < best_score:
				best_score = score
				best_gold = gold_pos
				best_path = path

		return best_gold, best_path

	def move(self, status):
		self.update_map(status)
		start = (status.x, status.y)

		if not status.goldPots:
			return []

		danger = self.predict_danger_tiles(status)

		gold, path = self.choose_best_gold_target(start, status, danger)

		# fallback: if all safe paths fail, try again without danger filtering
		if gold is None:
			gold, path = self.choose_best_gold_target(start, status, set())

		if gold is None:
			return []

		if gold == start:
			return []

		if not path:
			return []

		if self.safe_first_step(start, path[0], danger):
			return [path[0]]

		return []


players = [MyPlayer()]
