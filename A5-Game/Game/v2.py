#!/usr/bin/env python3
import random
from collections import deque

from game_utils import nameFromPlayerId
from game_utils import Direction as D, MoveStatus
from game_utils import Tile, TileStatus, TileObject
from game_utils import Map, Status
from simulator import Simulator
from player_base import Player

class MyPlayer(Player):

	def reset(self, player_id, max_players, width, height):
		self.player_name = "v2"
		self.width = width
		self.height = height
		self.known_map = Map(width, height)
    # counts visited tiles
		self.visit_count = {}
		self.recent_positions = deque(maxlen=12)

	def round_begin(self, r):
		pass

	def update_map(self, status):
		for x in range(status.map.width):
			for y in range(status.map.height):
				tile = status.map[x, y]
				if tile.status != TileStatus.Unknown:
					self.known_map[x, y].status = tile.status

	def breadth_first_search(self, start, goal, status):
		if start == goal:
			return []

		all_directions = list(D)
		queue = deque()
		queue.append((start, []))
		visited = {start}

		while queue:
			(cx, cy), path = queue.popleft()

			for direction in all_directions:
				dx, dy = direction.as_xy()
				nx, ny = cx + dx, cy + dy

				if nx < 0 or nx >= self.width or ny < 0 or ny >= self.height:
					continue
				if (nx, ny) in visited:
					continue
				if self.known_map[nx, ny].status == TileStatus.Wall:
					continue

				new_path = path + [direction]

				if (nx, ny) == goal:
					return new_path

				visited.add((nx, ny))
				queue.append(((nx, ny), new_path))

		return []
# chooses based on path length and gold amount
	def choose_best_gold_target(self, start, status):
		best_gold = None
		best_path = None
		best_score = None

		for gold_pos, amount in status.goldPots.items():
			path = self.breadth_first_search(start, gold_pos, status)
			if not path and gold_pos != start:
				continue

			score = (len(path), -amount)

			if best_score is None or score < best_score:
				best_score = score
				best_gold = gold_pos
				best_path = path

		return best_gold, best_path
# based on visited tiles and walls chooses next step
	def choose_exploration_move(self, status):
		options = []

		for direction in D:
			dx, dy = direction.as_xy()
			nx, ny = status.x + dx, status.y + dy

			if not (0 <= nx < self.width and 0 <= ny < self.height):
				continue
			if self.known_map[nx, ny].status == TileStatus.Wall:
				continue

			visit_penalty = self.visit_count.get((nx, ny), 0)
			recent_penalty = 5 if (nx, ny) in self.recent_positions else 0
			unknown_bonus = -3 if self.known_map[nx, ny].status == TileStatus.Unknown else 0

			score = visit_penalty + recent_penalty + unknown_bonus
			options.append((score, direction, (nx, ny)))

		if not options:
			return []

		options.sort(key=lambda x: x[0])
		return [options[0][1]]

	def move(self, status):
		self.update_map(status)
		start = (status.x, status.y)

		self.visit_count[start] = self.visit_count.get(start, 0) + 1
		self.recent_positions.append(start)
# calls function so move can be made based on gold 
		if status.goldPots:
			gold, path = self.choose_best_gold_target(start, status)
			if path:
				return [path[0]]
			if gold == start:
				return []

		return self.choose_exploration_move(status)

players = [MyPlayer()]