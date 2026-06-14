#!/usr/bin/env python3

from collections import deque

from game_utils import nameFromPlayerId
from game_utils import Direction as D, MoveStatus
from game_utils import Tile, TileStatus, TileObject
from game_utils import Map, Status
from simulator import Simulator
from player_base import Player


class MyPlayer(Player):

	def reset(self, player_id, max_players, width, height):
		self.player_name = "Bot5"
		self.player_id = player_id
		self.width = width
		self.height = height
		self.known_map = Map(width, height)
		# track how often we visit each tile
		self.visit_count = {}
		# remember last few positions so we dont go back and forth
		self.recent_positions = deque(maxlen=12)
		# rember gold hisotry --> maxlen can potentially be changed later on but this is just what I thought makes sense for now
		self.gold_history = deque(maxlen=10) # deque https://www.geeksforgeeks.org/python/deque-in-python/
		# what do we do if pot not in reach logic
		self.last_pot_pos = None
		# needed in dodge oponents: tracks opponents more closer so we dont just avoid all 8 tiles
		self.last_opponent_positions = {}
		# map type, we decide this after a few rounds (not from one random drop)
		self.map_mode = None     # "maze" or "open"
		self.rounds_seen = 0     # own round counter

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

	# measures avg open neighbours per known empty tile to tell maze vs open apart
	# corridors sit around 2, open areas around 6-7
	def measure_openness(self):
		total = 0
		count = 0
		for x in range(self.width):
			for y in range(self.height):
				if self.known_map[x, y].status != TileStatus.Empty:
					continue
				for direction in D:
					dx, dy = direction.as_xy()
					nx, ny = x + dx, y + dy
					if not (0 <= nx < self.width and 0 <= ny < self.height):
						continue
					if self.known_map[nx, ny].status == TileStatus.Empty:
						total += 1
				count += 1
		# dont judge until weve actually explored a bit
		if count < 12:
			return None
		return total / count

	def breadth_first_search(self, start, goal, status, danger=None):
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
	def choose_best_gold_target(self, start, status, danger=None):

		best_gold = None
		best_path = None
		best_score = None

		for gold_pos, amount in status.goldPots.items():
			path = self.breadth_first_search(start, gold_pos, status, danger) # added danger here so we can avoid tiles where opponents might step into
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

	# Update: Implementation we talked about making bots risk behaviour depencdant on current health and gold
	def max_sprint_length(self, status):
		health_ratio = status.health / status.params.maxHealth

		if health_ratio > 0.9:
			health_limit = 7 # sprint up to 7 steps when healthy
		elif health_ratio > 0.6:
			health_limit = 5
		elif health_ratio > 0.3:
			health_limit = 3
		else:
			health_limit = 1  # if its lower than 0.3 dont risk anything


		# keeping also gold reserves in mind and making it dependant on health status if we have low health we will use less steps anyways
		if health_limit >= 7:
			buffer = 30 # if healthy we want to move more
		elif health_limit >= 5:
			buffer = 15
		elif health_limit >= 3:
			buffer = 10
		else:
			buffer = 5

		# finding the longest sprint we can take while still keeping health and gold reserves in a safe range
		gold_limit = 0
		for steps in range(1, 8):
			cost_steps = sum(range(1, steps + 1))
			if cost_steps + buffer <= status.gold:
				gold_limit = steps
			else:
				break

		return min(health_limit, gold_limit)

	# setting profit margign dynamically so it depends on how well we performed in previous rounds
	def profit_margin (self, status):
		# needs some rounds to judge trend
		if len(self.gold_history) < 4:
			return 30

		growth = self.gold_history[-1] - self.gold_history[0]

		if growth > 20:
			return 1
		elif growth > 5:
			return 10
		elif growth > 0:
			return 20
		else:
			return 5 # be more aggresive if we have nothing to lose

	# crash avoidance based on health
	def crash_caution_level(self, status):

		health_ratio = status.health / status.params.maxHealth

		if health_ratio > 0.7:
			return 0   # plenty of HP --> ressive and dont care much about crashing
		else:
			return 1

	def predict_danger_tiles(self, status):
		danger = set()
		current_opponent_positions = {}

		gold_target  = None
		if status.goldPots:
			gold_target = next(iter(status.goldPots))

		for x in range(self.width):
			for y in range(self.height):
				tile = self.known_map[x, y]

				if tile.obj is None or not tile.obj.is_player():
					continue
				if tile.obj.is_player(self.player_id):
					continue

				opponent_id = tile.obj.as_player()
				opponent_position = (x, y)
				current_opponent_positions[opponent_id] = opponent_position # rember visible opponents pos to compare it next round and predict where they might go

				predicted_position = None

				# assumption 1 --> is chasing gold
				if gold_target is not None:
					gold_x, gold_y = gold_target

					step_x=0
					step_y=0

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

					# only use next step if inside map and not wall or something else
					if 0 <= next_x < self.width and 0 <= next_y < self.height:
						if not self.known_map[next_x, next_y].is_blocked():
							predicted_position = (next_x, next_y)


				# assumption 2 --> is going straight (based on assumption no gold target just savety maybe it would be better if we write something that if opponent not in reach of gold pot)
				if predicted_position is None:
					if opponent_id in self.last_opponent_positions:
						last_position = self.last_opponent_positions[opponent_id]

						# opponent stood still
						if last_position == opponent_position:
							predicted_position = opponent_position

						# opponent moved in a direction
						else:
							last_x, last_y = last_position

							move_x = x - last_x
							move_y = y - last_y
							next_x = x + move_x
							next_y = y + move_y

							# only use next step if inside map and not wall or something else
							if 0 <= next_x < self.width and 0 <= next_y < self.height:
								if not self.known_map[next_x, next_y].is_blocked():
									predicted_position = (next_x, next_y)

				if predicted_position is not None:
					danger.add(predicted_position)

		self.last_opponent_positions = current_opponent_positions
		return danger

	def should_dodge(self, status):
		# is anyone right next to us this round
		me = (status.x, status.y)
		for x in range(self.width):
			for y in range(self.height):
				tile = self.known_map[x, y]
				if tile.obj is None or not tile.obj.is_player():
					continue
				if tile.obj.is_player(self.player_id):
					continue
				if max(abs(x - me[0]), abs(y - me[1])) == 1:
					return True
		return False

	# Bot performed poorly in dense maize maps so I thought maybe we should sprint less if we dont know path
	def path_fully_known(self, start, path):
		x, y = start
		for d in path:
			dx, dy = d.as_xy()
			x, y = x + dx, y + dy
			if self.known_map[x, y].status != TileStatus.Empty:
				return False
		return True

	def move(self, status):
		self.gold_history.append(status.gold)
		self.update_map(status)
		start = (status.x, status.y)

		self.rounds_seen += 1

		# decide map type once, but only after round 3 (one starting spot tells us nothing)
		if self.map_mode is None and self.rounds_seen >= 3:
			openness = self.measure_openness()
			if openness is not None:
				# below ~3.5 means tight corridors --> maze. threshold can be tuned w/ batch runs
				self.map_mode = "maze" if openness < 3.5 else "open"

		self.visit_count[start] = min(self.visit_count.get(start, 0) + 1, 3) # Added panalty cap at 3
		self.recent_positions.append(start)

		# this is to figure out which tiles nearby oponents might step into so we dont crash
		danger = self.predict_danger_tiles(status)

		# if we are healthy enough we can ignore danger and stay aggressive
		if self.crash_caution_level(status) == 0:
			danger = set()

		def safe_step(direction):
			dx, dy = direction.as_xy()
			return (start[0] + dx, start[1] + dy) not in danger

		# dodge if someone is right next to us and we have nothing better to do (e.g. no gold path)
		if self.should_dodge(status) and not status.goldPots:
			for d in D:
				dx, dy = d.as_xy()
				nx, ny = start[0] + dx, start[1] + dy
				if (nx, ny) in danger:
					continue
				if not self.is_safe_tile(nx, ny):
					continue
				return [d]

		# calls function so move can be made based on gold
		if status.goldPots:
			gold, path = self.choose_best_gold_target(start, status, danger) # also added danger

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
					if explore_path and safe_step(explore_path[0]):
						return [explore_path[0]]
					explore = self.choose_exploration_move(status)
					if explore and safe_step(explore[0]):
						return explore
					return []

				# sprint if gold is worth it and the first step isnt risky
				if (steps <= self.max_sprint_length(status)
					and gold_amount - cost > self.profit_margin(status)
					and safe_step(path[0])
					and self.path_fully_known(start, path)):
					if self.am_i_closest(status, gold, start):
						return path

				# maze: usually only one way through, so dont freeze --> take the step even if risky
				if self.map_mode == "maze":
					return [path[0]]

				# open map: keep the safe behaviour
				if safe_step(path[0]):
					return [path[0]]
				# otherwise let exploration handle it below

		explore_path = self.find_nearest_unknown(start)
		if explore_path and safe_step(explore_path[0]):
			return [explore_path[0]]

		# fall back to scored exploration, also only if its safe
		explore = self.choose_exploration_move(status)
		if explore and safe_step(explore[0]):
			return explore

		# nothing safe to do --> just wait this round
		return []


players = [MyPlayer()]