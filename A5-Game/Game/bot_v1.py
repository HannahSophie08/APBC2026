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
		
		self.player_name = "Bot4"
		self.width = width
		self.height = height 
		self.known_map = Map(width, height)
		
	

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

				# skip neighbors if out of bounds, already vistied, or known wall
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
		
		# no path found 
		return []
				
		
	def move(self, status):
		
		self.update_map(status)
		start = (status.x, status.y)
		
		gold = next(iter(status.goldPots.keys()))
		path = self.breadth_first_search(start, gold, status)

		if path:
			return [path[0]]
		
		else: # if no path is returned, explore randomly 

			options = []
			for direction in D:
				dx, dy = direction.as_xy()
				nx, ny = status.x + dx, status.y + dy
				if 0 <= nx < self.width and 0 <= ny < self.height:
					if self.known_map[nx, ny].status != TileStatus.Wall:
						options.append(direction)
			if options:
				return [random.choice(options)]
			return []


players = [MyPlayer()]


