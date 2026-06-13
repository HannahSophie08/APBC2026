#!/usr/bin/env python3

from collections import deque

from game_utils import nameFromPlayerId
from game_utils import Direction as D, MoveStatus
from game_utils import Tile, TileStatus, TileObject
from game_utils import Map, Status
from simulator import Simulator
from player_base import Player


# only the 4 orthogonal dirs, used for exits/corridor checks so diagonals dont fake a junction
ORTHO = [D.up, D.down, D.left, D.right]


class MyPlayer(Player):

	def reset(self, player_id, max_players, width, height):
		self.player_name = "HannahV3"
		self.player_id = player_id
		self.width = width
		self.height = height
		self.known_map = Map(width, height)
		# remember last few positions so we dont go back and forth
		self.recent_positions = deque(maxlen=12)
		# rember gold hisotry --> maxlen can potentially be changed later on but this is just what I thought makes sense for now
		self.gold_history = deque(maxlen=10) # deque https://www.geeksforgeeks.org/python/deque-in-python/
		# map type, we decide this after a few rounds (not from one random drop)
		self.rounds_seen = 0     # own round counter

		# short window only for cycle detection, longer history wastes memory and hides fresh cycles
		self.position_history = deque(maxlen=8)

		# heatmap: how often we stood on each tile, high counts mean we keep re-treading dead ground
		self.visit_count = {}
		# tiles we already proved hold no frontier behind them, never worth exploring into again
		self.dead_ends = set()
		# the frontier we committed to, we keep walking to it instead of replanning every round
		self.explore_target = None
		# last step we took, lets us keep momentum through corridors instead of flip flopping
		self.last_direction = None

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

	# chooses by expected profit, gold minus the cost of getting there
	def choose_best_gold_target(self, start, status, danger=None):

		best_gold = None
		best_path = None
		best_score = None

		for gold_pos, amount in status.goldPots.items():
			path = self.breadth_first_search(start, gold_pos, status, danger) # danger here so we avoid tiles opponents might step into
			if not path and gold_pos != start:
				continue

			steps = len(path)
			# sprint cost grows quadratically so longer trips eat the payout fast
			cost = sum(range(1, steps + 1)) if steps else 0
			profit = amount - cost

			# more profit wins, tie break on the shorter path so we still react quickly
			score = (profit, -steps)

			if best_score is None or score > best_score:
				best_score = score
				best_gold = gold_pos
				best_path = path

		return best_gold, best_path


	def borders_unknown(self, x, y):
		# frontier tile = a tile we already know is empty, sitting right next to something unexplored
		for direction in D:
			dx, dy = direction.as_xy()
			nx, ny = x + dx, y + dy
			if not (0 <= nx < self.width and 0 <= ny < self.height):
				continue
			if self.known_map[nx, ny].status == TileStatus.Unknown:
				return True
		return False

	def info_gain(self, x, y):
		# estimate how much a frontier opens up, count unknowns in a 5x5 window around it
		# big empty regions score high, single trapped unknowns score low so we skip crumbs
		gain = 0
		for ax in range(x - 2, x + 3):
			for ay in range(y - 2, y + 3):
				if not (0 <= ax < self.width and 0 <= ay < self.height):
					continue
				if self.known_map[ax, ay].status == TileStatus.Unknown:
					gain += 1
		return gain

	def collect_frontiers(self, start):
		# one bfs over known-safe tiles, returns every reachable frontier with its distance and path
		# dead ends fix themselves: a fully explored sackgasse holds no frontier so it never shows up
		queue = deque()
		queue.append((start, []))
		visited = {start}
		frontiers = {}

		while queue:
			(cx, cy), path = queue.popleft()

			if path and self.borders_unknown(cx, cy):
				frontiers[(cx, cy)] = path
				# dont expand past a frontier, the tiles behind it are unknown anyway

			for direction in D:
				dx, dy = direction.as_xy()
				nx, ny = cx + dx, cy + dy
				if (nx, ny) in visited:
					continue
				# exploration walks through known-safe tiles only (no unknowns, no players)
				if not self.is_safe_tile(nx, ny, allow_unknown=False):
					continue
				visited.add((nx, ny))
				queue.append(((nx, ny), path + [direction]))

		return frontiers

	def pick_explore_target(self, start):
		# score frontiers by information_gain / distance, biggest reveal per step wins
		# divide by visit count so re-treaded ground gets demoted, skip known dead ends entirely
		frontiers = self.collect_frontiers(start)
		if not frontiers:
			return None, None

		best_pos = None
		best_path = None
		best_score = None

		for pos, path in frontiers.items():
			if pos in self.dead_ends:
				continue
			dist = max(1, len(path))
			gain = self.info_gain(*pos)
			if gain == 0:
				continue
			visits = self.visit_count.get(pos, 0)
			score = (gain / dist) / (1 + visits)

			if best_score is None or score > best_score:
				best_score = score
				best_pos = pos
				best_path = path

		return best_pos, best_path

	def explore_step(self, start, status):
		# 1. keep the committed target if it still borders unknown and is reachable
		path = None
		if self.explore_target is not None:
			if self.explore_target == start or not self.borders_unknown(*self.explore_target):
				# reached it or it filled in, that ground is done, dont chase it again
				self.dead_ends.add(self.explore_target)
				self.explore_target = None
			else:
				path = self.breadth_first_search(start, self.explore_target, status, danger=None)
				if not path:
					self.explore_target = None

		# 2. no valid target, pick the best frontier and commit to it
		if self.explore_target is None:
			target, path = self.pick_explore_target(start)
			if target is None:
				# nothing left to reveal, stop wandering and bank
				return []
			self.explore_target = target

		if not path:
			return []

		# 3. corridor momentum + oscillation guard before we commit the step
		step = self.choose_step(start, path)
		return [step] if step is not None else []

	def exits(self, x, y):
		# walkable orthogonal neighbours, used to tell corridors from junctions
		out = []
		for direction in ORTHO:
			dx, dy = direction.as_xy()
			nx, ny = x + dx, y + dy
			if self.is_safe_tile(nx, ny, allow_unknown=True):
				out.append(direction)
		return out

	def in_short_cycle(self):
		# catch any back-and-forth of period 2 to 4, not just plain ABAB
		positions = list(self.position_history)
		for period in (2, 3, 4):
			if len(positions) >= period * 2:
				tail = positions[-period * 2:]
				if tail[:period] == tail[period:]:
					return True
		return False

	def choose_step(self, start, path):
		# default is just the next step of the planned path
		step = path[0]
		dx, dy = step.as_xy()
		nxt = (start[0] + dx, start[1] + dy)

		# corridor momentum: inside a 1-2 exit tile, dont reverse onto where we came from
		# turning around in a corridor wastes rounds, push on toward the junction instead
		if self.last_direction is not None and len(self.exits(*start)) <= 2:
			back = self.reverse(self.last_direction)
			if step == back:
				forward = (start[0] + self.last_direction.as_xy()[0],
				           start[1] + self.last_direction.as_xy()[1])
				if self.is_safe_tile(*forward, allow_unknown=True) and forward not in self.dead_ends:
					return self.last_direction

		# oscillation guard: if we are bouncing in a tiny loop, break to the least visited neighbour
		if self.in_short_cycle():
			best_d = None
			best_v = None
			for direction in D:
				ddx, ddy = direction.as_xy()
				nx, ny = start[0] + ddx, start[1] + ddy
				if not self.is_safe_tile(nx, ny):
					continue
				v = self.visit_count.get((nx, ny), 0)
				if best_v is None or v < best_v:
					best_v = v
					best_d = direction
			if best_d is not None:
				return best_d

		return step

	def reverse(self, direction):
		# opposite step, used to detect a corridor u-turn
		return {
			D.up: D.down, D.down: D.up,
			D.left: D.right, D.right: D.left,
			D.up_left: D.down_right, D.down_right: D.up_left,
			D.up_right: D.down_left, D.down_left: D.up_right,
		}[direction]

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
			return 10

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
		# simpler local model: we dont guess opponent intent, we just block every tile
		# they could step into next round. the old gold-chasing guess was noisy and often wrong
		danger = set()
		if not status.others:
			return danger

		for other in status.others:
			if other is None:
				continue
			ox, oy = other.x, other.y
			danger.add((ox, oy))
			for direction in D:
				dx, dy = direction.as_xy()
				nx, ny = ox + dx, oy + dy
				if 0 <= nx < self.width and 0 <= ny < self.height:
					if not self.known_map[nx, ny].is_blocked():
						danger.add((nx, ny))
		return danger

	def should_dodge(self, status):
		# is anyone right next to us this round
		if not status.others:
			return False
		me = (status.x, status.y)
		for other in status.others:
			if other is None:
				continue
			if max(abs(other.x - me[0]), abs(other.y - me[1])) == 1:
				return True
		return False


	def known_prefix(self, path, start):
		# longest leading chunk of the path that stays on KNOWN-empty tiles
		out = []
		cx, cy = start
		for d in path:
			dx, dy = d.as_xy()
			cx, cy = cx + dx, cy + dy
			t = self.known_map[cx, cy]
			if t.status == TileStatus.Empty and not (t.obj is not None and t.obj.is_player()):
				out.append(d)
			else:
				break
		return out

	def move(self, status):
		self.gold_history.append(status.gold)
		self.update_map(status)
		start = (status.x, status.y)

		self.rounds_seen += 1

		self.recent_positions.append(start)
		self.position_history.append(start)
		# bump the heatmap, frequently visited tiles get demoted during exploration scoring
		self.visit_count[start] = self.visit_count.get(start, 0) + 1

		# track movement so a returned step can update last_direction for corridor momentum
		def commit(moves):
			if moves:
				self.last_direction = moves[0]
			return moves

		# figure out which tiles nearby opponents might step into so we dont crash
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
				return commit([d])

		# calls function so move can be made based on gold
		if status.goldPots:
			gold, path = self.choose_best_gold_target(start, status, danger) # also added danger
			# if danger is blocking all paths to gold, retry ignoring danger
			if not path and status.goldPots:
				gold, path = self.choose_best_gold_target(start, status, danger=set())

			if gold == start:
				return []

			if path:
				gold_amount = status.goldPots[gold]
				steps = len(path)

				sprint = max(1, self.max_sprint_length(status))
				rounds_needed = -(-steps // sprint)
				if rounds_needed > status.goldPotRemainingRounds:
					# unreachable in time: dont burn gold chasing it.
					# a profitable pot is worth dropping the explore target for, so clear it
					self.explore_target = None
					return commit(self.explore_step(start, status))

				# gold this rich overrides whatever frontier we were committed to
				self.explore_target = None

				# only queue moves through known-empty tiles, capped by sprint budget
				known = self.known_prefix(path, start)
				actual_steps = min(len(known), sprint)

				if actual_steps == 0:
					# next tile toward gold is unseen -> one step to reveal it
					return commit([path[0]])

				actual_cost = sum(range(1, actual_steps + 1))
				if gold_amount > actual_cost and safe_step(path[0]):
					return commit(path[:actual_steps])

				return commit([path[0]])

		# explore using the committed target + scored frontiers
		explore = self.explore_step(start, status)
		if explore:
			return commit(explore)

		# nothing useful to do, bank instead of wandering
		return []
players = [MyPlayer()]