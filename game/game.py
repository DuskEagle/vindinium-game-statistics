from collections import deque
import numpy as np
import re

AIM = {"North": (0, -1),
       "East": (1, 0),
       "South": (0, 1),
       "West": (-1, 0),
       "Stay": (0, 0)}

AIM_INVERSE = {value: key for key, value in AIM.items()}

class Tile:
    AIR = 0
    WALL = 1
    TAVERN = 2
    MINE = 3
    HERO = 4
    
    def __init__(self, type, heroId = None):
        self.type = type
        if heroId == None or heroId == "-":
            self.heroId = None
        else:
            self.heroId = int(heroId)

class Game:
    MINE_COST = 20 # Costs 20hp to take a mine
    TAVERN_HEALTH = 50
    TAVERN_COST = 2
    HERO_MAX_HEALTH = 100
    HERO_ATTACK_POWER = 20
    
    def __init__(self, state, playing_game):
        """ playing_game: The JSON we receive is slightly different if we are
        actively playing a game or if we are observing a game. """
        self.playing_game = playing_game
        self.state = state
        self.gameId = state["game"]["id"]
        self.turn = state["game"]["turn"]
        self.max_turns = state["game"]["maxTurns"]
        self.hero_turn = self.turn // 4
        self.max_hero_turns = self.max_turns // 4
        self.board = Board(state["game"]["board"])
        self.heroes = [Hero(state["game"]["heroes"][i]) for i in range(len(state["game"]["heroes"]))]
        self.mine_locs = set()
        self.tavern_locs = set()
        for x in range(len(self.board.tiles)):
            for y in range(len(self.board.tiles[x])):
                obj = self.board.tiles[x][y]
                if obj.type == Tile.MINE:
                    self.mine_locs.add((x,y))
                elif obj.type == Tile.TAVERN:
                    self.tavern_locs.add((x, y))
        self.finished = state["game"]["finished"]
        if self.playing_game:
            self.hero = list(filter(lambda hero : hero.heroId == state["hero"]["id"], self.heroes))[0]
            self.enemy_heroes = list(filter(lambda hero : hero.heroId != self.hero.heroId, self.heroes))
    
    def getHeroByHeroId(self, heroId, hero_list=None):
        if hero_list == None:
            hero_list = self.heroes
            # Doing it this way because we can"t reference "self" in the function args
        
        found_heroes = list(filter(lambda hero : hero.heroId == tile.heroId, hero_list))
        if len(found_heroes) == 1:
            return hero[0]
        return None
    
    def heroesInRange(self, pos, r):
        """Return list of heroes within r of pos, unsorted.
        
        The heroes could be separated by impassable terrain. Use aStar or some other method
        to determine if they are reachable in r steps if that is desired."""
        return list(filter(lambda hero : Board.l1Distance(pos, hero.pos) <= r, self.heroes))
    
    def meaningfulDirection(self, loc, direction):
        return self.board.meaningfulDirection(loc, direction)
    
    def updateForNewHeroPosition(self, hero, oldPos):
        """This is only necessary when simulating a game. After sending a move
        command to the server, you do not need to call this, as the server
        will send back a new game state anyway."""
        self.board.updateForNewHeroPosition(hero, oldPos)
    
    @staticmethod
    def getFreshlyDeadHeroes(old_game, new_game):
        """ Input: Two game states of the same game, separated by exactly one
        turn (NOT one hero turn). The "heroes" property should be in the same
        order for both game states. (It should be that way anyway - hero 1
        should be in position 0, hero 2 in position 1, etc. There's no reason
        to ever change this.)
        
        Output: A list of the heroes that died between the two turns.
        
        This function relies on the assumption that hero spawn points are never
        adjacent to each other. This is a correct assumption based on the
        current (Oct 2014) vindinium map generation code, and there's little
        reason for that to ever change. """
        
        assert old_game.turn + 1 == new_game.turn
        
        heroHealthFunction = lambda hero_list: list(map(lambda hero: hero.health, hero_list))
        heroPosFunction = lambda hero_list: list(map(lambda hero: hero.pos, hero_list))
        
        hero_health_diff = np.subtract(heroHealthFunction(new_game.heroes), heroHealthFunction(old_game.heroes))
        hero_pos_diff = list(map(lambda pos1, pos2: Board.l1Distance(pos1, pos2), 
            heroPosFunction(new_game.heroes), heroPosFunction(old_game.heroes)))
        
        freshly_dead_heroes = []
        for i in range(4):
            """ We determine if a hero has died if:
            1. Their health has gone up by more than Game.TAVERN_HEALTH in one turn
            2. Or, their position has changed by more than 1 (this condition could be
                trigged without the first if the hero was spawnkilled). """
            if hero_health_diff[i] > Game.TAVERN_HEALTH or hero_pos_diff[i] > 1:
                freshly_dead_heroes.append(new_game.heroes[i])
                
        return freshly_dead_heroes

class Board:
    def __parseTile(self, string):
        if string == "  ":
            return Tile(Tile.AIR)
        if string == "##":
            return Tile(Tile.WALL)
        if string == "[]":
            return Tile(Tile.TAVERN)
        match = re.match("\$([-0-9])", string)
        if match:
            return Tile(Tile.MINE, match.group(1))
        match = re.match("\@([0-9])", string)
        if match:
            return Tile(Tile.HERO, match.group(1))

    def __parseTiles(self, tiles):
        vector = [tiles[i:i+2] for i in range(0, len(tiles), 2)]
        matrix = [vector[i:i+self.size] for i in range(0, len(vector), self.size)]

        return np.transpose([[self.__parseTile(x) for x in xs] for xs in matrix]).copy()

    def __init__(self, board=None, zeroPos=None):
        """ Must pass board argument unless being called internally to this class 
        
        (Unimplemented) If zeroPos != None, then from zeroPos calculate the distance
        each other tile on the board is from zeroPos, factoring in walls and other
        permanently impassable terrain."""
        if board != None:
            self.size = board["size"]
            self.tiles = self.__parseTiles(board["tiles"])
            if zeroPos != None:
                raise NotImplementedError("Not implemented yet")

    def __copy__(self):
        newBoard = Board()
        newBoard.size = self.size
        newBoard.tiles = []
        for x in range(len(self.tiles)):
            newBoard.tiles.append([])
            for y in range(len(self.tiles[x])):
                newBoard.tiles[x].append(Tile(self.tiles[x][y].type, self.tiles[x][y].heroId))
        return newBoard

    def tile(self, loc):
        return self.tiles[loc[0]][loc[1]]

    def passable(self, loc):
        """ True if hero can walk to loc, ignoring if a hero is currently
        there, """
        x, y = loc
        pos = self.tiles[x][y]
        return (pos.type != Tile.WALL) and (pos.type != Tile.TAVERN) and (pos.type != Tile.MINE)
    
    def bfs(self, loc, path_through_heroes, fill_value=float("inf")):
        """ Return a 2d array of the board, with each element being an int 
        representing the distance from loc to that element, or float("inf")
        if the tile is unreachable. If a tile is impassable, it will still
        receive a value, but the bfs will not continue through it.
        
        path_through_heroes(bool): If true, then allow walking through locations
        heroes currently occupy. If false, then the locations of the heroes
        themselves will still have a non-infinite value, but pathing will be
        forced to go around those locations rather than through.
        
        fill_value(number): Value for tiles that are unreachable from loc. """
        distance_map = [[fill_value for x in range(self.size)] for y in range(self.size)]
        distance_map[loc[0]][loc[1]] = 0
        
        seen = {loc}
        queue = deque([loc])
        
        while len(queue) > 0:
            cur_loc = queue.popleft()
            cur_loc_cost = distance_map[cur_loc[0]][cur_loc[1]]
            
            for direction in AIM:
                next_loc = self.to(cur_loc, direction)
                if next_loc in seen:
                    continue
                distance_map[next_loc[0]][next_loc[1]] = cur_loc_cost + 1
                seen.add(next_loc)
                if self.passable(next_loc) \
                    and (path_through_heroes or self.tile(next_loc).type != Tile.HERO):
                    queue.append(next_loc)
        
        return distance_map
    
    def heroIdsInRange(self, loc, r):
        """Return list of heroes within r of pos, unsorted."""
        hero_ids_in_range = []
        for x in range(len(self.tiles)):
            for y in range(len(self.tiles[x])):
                if self.tiles[x][y].type == Tile.HERO and Board.l1Distance(loc, (x,y)) <= r:
                    hero_ids_in_range.append(self.tiles[x][y].heroId)
        return hero_ids_in_range

    def to(self, loc, direction, stay_on_impassable=False):
        """ Calculate a new location given the direction. 
        
        If stay_on_impassable == True, then if a wall, tavern, mine, or hero is
        on the resulting location, then return the current loc, as if direction
        had been "Stay". """
        x, y = loc
        d_x, d_y = AIM[direction]
        n_x = x + d_x
        if (n_x < 0): n_x = 0
        if (n_x >= self.size): n_x = self.size - 1
        n_y = y + d_y
        if (n_y < 0): n_y = 0
        if (n_y >= self.size): n_y = self.size - 1
        if stay_on_impassable:
            tile = self.tile((n_x, n_y))
            if tile.type == Tile.WALL or tile.type == Tile.TAVERN \
                or tile.type == Tile.MINE or tile.type == Tile.HERO:
                return loc

        return (n_x, n_y)

    def updateForNewHeroPosition(self, hero, oldPos):
        """This is only necessary when simulating a game. After sending a move
        command to the server, you do not need to call this, as the server
        will send back a new game state anyway."""
        self.tiles[oldPos[0]][oldPos[1]] = Tile(Tile.AIR)
        self.tiles[hero.pos[0]][hero.pos[1]] = Tile(Tile.HERO, hero.heroId)

    def meaningfulDirection(self, loc, direction):
        """Returns true if issuing the direction command from loc
        will be any different from issuing "Stay". For example, moving
        into a mine is meaningful, but moving into a hero, off of the
        map, or onto a wall is not meaningful.
        
        This is not entirely comprehensive, for example a hero moving
        into their own mine will still be counted as meaningful by this
        function. This behavior should not be relied on, as this may
        get improved in the future.
        
        The direction "Stay" itself is considered meaningful."""
        if direction == "Stay":
            return True
        x, y = loc[0], loc[1]
        d_x, d_y = AIM[direction]
        n_x, n_y = x + d_x, y + d_y
        if n_x < 0 or n_y < 0 or n_x >= self.size or n_y >= self.size:
            return False
        terrain = self.tile((n_x, n_y))
        if terrain.type == Tile.WALL or terrain.type == Tile.HERO:
            return False
        return True

    @staticmethod
    def l1Distance(loc1, loc2):
        """ Return the L1 (Manhattan) distance between two locs """
        return abs(loc1[0] - loc2[0]) + abs(loc1[1] - loc2[1])

    @staticmethod
    def locListToDirections(loc_list):
        
        if len(loc_list) <= 1:
            return "Stay"
    
        result = []
        previous_loc = loc_list[0]
        for next_loc in loc_list[1:]:
            x_dir, y_dir = next_loc[0] - previous_loc[0], next_loc[1] - previous_loc[1]
            result.append(AIM_INVERSE[(x_dir, y_dir)]) # Exception if next_loc not adjacent to previous_loc
            previous_loc = next_loc
            
        return result
    
    @staticmethod
    def locListToFirstDirection(loc_list):
        if len(loc_list) <= 1:
            return "Stay"
        
        start_loc = loc_list[0]
        next_loc = loc_list[1]
        x_dir, y_dir = next_loc[0] - start_loc[0], next_loc[1] - start_loc[1]
        return AIM_INVERSE[(x_dir, y_dir)] # Exception if next_loc not adjacent to previous_loc
    

class Hero:
    def __init__(self, hero):
        self.name = hero["name"]
        self.heroId = hero["id"]
        self.userId = hero["userId"]
        self.elo = hero["elo"]
        # NOTE: The state we receive from the server has the x and y
        # values backward. We fix that here.
        self.pos = (hero["pos"]["y"],hero["pos"]["x"])
        self.spawn_pos = (hero["spawnPos"]["y"],hero["spawnPos"]["x"])
        # last_direction is one of AIM.keys() or None.
        self.last_direction = hero.get("lastDir")
        self.health = hero["life"]
        self.gold = hero["gold"]
        self.mine_count = hero["mineCount"]
        self.crashed = hero["crashed"]
