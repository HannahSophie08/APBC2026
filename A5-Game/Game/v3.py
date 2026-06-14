#!/usr/bin/env python3
import random # brauchen wir ja eigentlich nicht mehr oder? FIX!
from collections import deque

from game_utils import nameFromPlayerId
from game_utils import Direction as D, MoveStatus
from game_utils import Tile, TileStatus, TileObject
from game_utils import Map, Status
from simulator import Simulator
from player_base import Player


class MyPlayer(Player):
 
	def reset(self, player_id, max_players, width, height):
		self.player_name = "v3"
		self.player_id = player_id
		self.width = width
		self.height = height
		self.known_map = Map(width, height)
		# track how often we visit each tile
		self.visit_count = {}
		# remember last few positions so we dont go back and forth
		self.recent_positions = deque(maxlen=12)
 
	def round_begin(self, r):
		pass

	def set_mines(self, status):
		return []
 
	def update_map(self, status):
		# clear old player/gold positions since they move each round
		for x in range(self.width):
			for y in range(self.height):
				self.known_map[x, y].obj = None
 
		for x in range(status.map.width):
			for y in range(status.map.height):
				tile = status.map[x, y]
				if tile.status != TileStatus.Unknown:
					self.known_map[x, y].status = tile.status
					self.known_map[x, y].obj = tile.obj
 
	# Check if a tile is safe to walk through.
	def is_safe_tile(self, x, y, allow_unknown=False):
		if not (0 <= x < self.width and 0 <= y < self.height):
			return False
 
		tile = self.known_map[x, y]
 
		# walls and mines block movement
		if tile.is_blocked():
			return False
 
		# dont path through tiles we havent seen yet --> UPDATE: I now sometimes allow unknown tiles because the bot eneded up being too cautious
		if tile.status == TileStatus.Unknown and not allow_unknown:
			return False
 
		# avoid other players (only the ones we can see) --> could still crash if another player moves into same field (FIX!)
		if tile.obj is not None and tile.obj.is_player():
			return False
 
		return True
 
	def breadth_first_search(self, start, goal, status):
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
				# allow unknowns when chasing gold so we dont get stuck waiting
				if not self.is_safe_tile(nx, ny, allow_unknown=True):
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
 
			# shorter path is better, if tied pick the one with more gold
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
 
			# allow unknowns so we actually explore
			if not self.is_safe_tile(nx, ny, allow_unknown=True):
				continue
 
			# prefer tiles we havent visited much and unknown areas
			visit_penalty = self.visit_count.get((nx, ny), 0)
			recent_penalty = 5 if (nx, ny) in self.recent_positions else 0
			unknown_bonus = -3 if self.known_map[nx, ny].status == TileStatus.Unknown else 0
 
			score = visit_penalty + recent_penalty + unknown_bonus
			options.append((score, direction))
 
		if not options:
			return []
 
		options.sort(key=lambda item: item[0])
		return [options[0][1]]
	
	# rough estimate: only compares visible players
	def am_i_closest(self, status, gold_pos, start):
		my_dist = max(abs(start[0] - gold_pos[0]), abs(start[1] - gold_pos[1]))
 
		for other in status.others:
			if other is None:
				continue
			other_dist = max(abs(other.x - gold_pos[0]), abs(other.y - gold_pos[1]))
			if other_dist < my_dist:
				return False
		return True
 
	# only when we cannot reach gold or when gold is not worth chasing.
	def find_nearest_unknown(self, start):
		
   		 # Here I allow stepping towards unknown tiles so the bot can discover more 
		queue = deque()
		queue.append((start, []))
		visited = {start}
 
		while queue:
			(cx, cy), path = queue.popleft()
 
			# found an unknown tile we can reach
			if self.known_map[cx, cy].status == TileStatus.Unknown and path:
				return path
 
			for direction in D:
				dx, dy = direction.as_xy()
				nx, ny = cx + dx, cy + dy
 
				if (nx, ny) in visited:
					continue
				if not (0 <= nx < self.width and 0 <= ny < self.height):
					continue
 
				tile = self.known_map[nx, ny]
				# walk through empty tiles while allowing stepping onto unknown ones
				if tile.is_blocked():
					continue
				if tile.obj is not None and tile.obj.is_player():
					continue
 
				visited.add((nx, ny))
				queue.append(((nx, ny), path + [direction]))
 
		return []
 
	def move(self, status):
		self.update_map(status)
		start = (status.x, status.y)
 
		self.visit_count[start] = min(self.visit_count.get(start, 0) + 1, 3) # Added panalty cap at 3
		self.recent_positions.append(start)

 		# calls function so move can be made based on gold 
		if status.goldPots:
			gold, path = self.choose_best_gold_target(start, status)
 
			if gold == start:
				return []
 
			if path:
				gold_amount = status.goldPots[gold]
				steps = len(path)
				# so we only sprint if the gold reward is clearly worth it (more steps more costs)
				cost = sum(range(1, steps + 1))
 
				# checks if pot will expire before we  get there 
				if steps > status.goldPotRemainingRounds:
					explore_path = self.find_nearest_unknown(start)
					if explore_path:
						return [explore_path[0]]
					return self.choose_exploration_move(status)
 
				# this will sprint to gold if its close at max 5 steps
				if steps <= 5 and cost < status.gold and gold_amount - cost > 30:
					if self.am_i_closest(status, gold, start):
						return path
 
				# default --> one step toward gold
				return [path[0]]
 
		explore_path = self.find_nearest_unknown(start)
		if explore_path:
			return [explore_path[0]]
 
		
		return self.choose_exploration_move(status)
 
 
players = [MyPlayer()]