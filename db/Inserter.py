import sys
sys.path.insert(0, "../game")

import ast
import datetime
import logging as _logging
import numpy as np
import psycopg2 as psycopg
from multiprocessing import Lock
from psycopg2.extras import Json

from game import Game

class Inserter():
    insert_user_lock = Lock()
    
    def __init__(self, database_name="vindinium", database_user="postgres", logger=_logging.getLogger("Inserter")):
        self.connection = psycopg.connect("dbname=" + database_name + " user=" + database_user)
        self.db = self.connection.cursor()
        self.logger = logger
    
    def insertGame(self, game_strings):
        """ game_strings : list of strings, each of which represents one turn
        of the same game. game_strings can also be a generator. """
        
        for index, turn_string in enumerate(game_strings):
            if index == 0:
                self._insertGame(turn_string)
                game = None
            
            turn_string = turn_string.rstrip("\n").rstrip("\r")
            if len(turn_string) > 0:
                game = self.insertTurn(turn_string, game)
                self.connection.commit()
        
        """ game.finished should always be true at this point, but in case of 
        any unexpected errors we check anyway. Worst case, we never set
        Games.finished to true in the DB and our queries will just ignore this
        game. """
        if game.finished:
            self._setGameFinished(game)
        self.connection.commit()
    
    def insertTurn(self, turn_string, old_game):
        """ Insert turn represented by turn_string into database. """
        
        state = Inserter._parseJson(turn_string)
        game = Game(state, False)
        if old_game is None:
            freshly_dead_heroes = []
        else:
            freshly_dead_heroes = Game.getFreshlyDeadHeroes(old_game, game)
        
        turn_id = self._insertTurnToDB(game, state)
        self.logger.debug("Game: " + str(game.gameId) + ", Turn: " + str(game.turn))
        
        hero_ids = []
        for hero in game.heroes:
            hero_ids.append(self._insertHeroToDB(game, hero, turn_id, hero in freshly_dead_heroes))
        
        self._insertMinesToDB(game, turn_id, hero_ids)
        
        return game
    
    def _insertGame(self, first_turn_string):
        state = Inserter._parseJson(first_turn_string)
        game = Game(state, False)
        self.logger.info("Inserting " + game.gameId + " to database.")
        
        self._insertGameToDB(game)
        self._insertOrUpdateBots(game)
    
    def _insertGameToDB(self, game):
        self.db.execute( \
            "INSERT INTO Games "
            "    (gameId, time, size, mineCount, finished) "
            "VALUES (%s, %s, %s, %s, %s);",
            (game.gameId, datetime.datetime.now(), game.board.size, \
            len(game.mine_locs), game.finished))
    
    def _insertOrUpdateBots(self, game):
        for hero in game.heroes:
            hero_dict = {"userId": hero.userId, "name": hero.name, "elo": hero.elo, \
                "lastGameId": game.gameId}
            
            self.db.execute(
                "UPDATE Bots "
                "    SET elo = %(elo)s "
                "WHERE userId = %(userId)s;",
                hero_dict)
            
            # Conditional insert if bot does not exist yet.
            # This may contain a race condition; see 
            # http://stackoverflow.com/a/13342031/2491377.
            # Thus, we wrap a lock around these inserts.
            try:
                Inserter.insert_user_lock.acquire()
                self.db.execute(
                    "INSERT INTO Bots (userId, name, elo) "
                    "SELECT %(userId)s, %(name)s, %(elo)s "
                    "WHERE NOT EXISTS "
                    "    (SELECT 1 FROM Bots WHERE userId = %(userId)s);",
                    hero_dict)
            
                self.db.execute(
                    "INSERT INTO HistoricalBots "
                    "    (userId, lastGameId, elo, previousHistoricalBotId) "
                    "VALUES (%(userId)s, %(lastGameId)s, %(elo)s, "
                    "    (SELECT hb.id FROM HistoricalBots hb "
                    "    LEFT JOIN HistoricalBots hb_later "
                    "        ON hb_later.userId = hb.userId "
                    "        AND hb_later.previousHistoricalBotId = hb.id "
                    "    WHERE hb.userId = %(userId)s "
                    "        AND hb_later.id IS NULL));",
                    hero_dict)
            
                self.connection.commit()
            finally:
                Inserter.insert_user_lock.release()
    
    @staticmethod
    def _parseJson (string):
        return ast.literal_eval("{\"game\":" + string.replace(":false}", ":False}").replace(":true}", ":True}") + "}")

    def _insertTurnToDB(self, game, state):
        self.db.execute(
            "INSERT INTO Turns "
            "    (gameId, turn) "
            "VALUES (%(gameId)s, %(turn)s) "
            "RETURNING id;",
            {"gameId": game.gameId, "turn": game.turn})
        return self.db.fetchone()[0]
    
    def _setGameFinished(self, game):
        self.db.execute(
            "UPDATE GAMES "
            "    SET finished = TRUE "
            "WHERE gameId = %s;",
            (game.gameId,))
    
    def _insertHeroToDB(self, game, hero, turn_id, died):
        bfs_map = game.board.bfs(hero.pos, False, fill_value=2**31-1)
        obstructed_bfs_map = game.board.bfs(hero.pos, True, fill_value=2**31-1)
        
        self.db.execute( \
            "INSERT INTO Heroes ( "
            "    userId, "
            "    gameId, "
            "    turnId, "
            "    inGameId, "
            "    life, "
            "    gold, "
            "    mineCount, "
            "    died, "
            "    pos, "
            "    spawnPos, "
            "    lastDir, "
            "    crashed, "
            "    heroDistances, "
            "    heroObstructedDistances, "
            "    tavernDistances, "
            "    tavernObstructedDistances, "
            "    mineDistances, "
            "    mineObstructedDistances) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING id;", \
            (hero.userId, \
            game.gameId, \
            turn_id, \
            hero.heroId, \
            hero.health, \
            hero.gold, \
            hero.mine_count, \
            died, \
            list(hero.pos), \
            list(hero.spawn_pos), \
            hero.last_direction, \
            hero.crashed, \
            [bfs_map[x][y] for x, y in map(lambda hero : hero.pos, game.heroes)], \
            [obstructed_bfs_map[x][y] for x, y in map(lambda hero : hero.pos, game.heroes)], \
            [bfs_map[x][y] for x, y in game.tavern_locs], \
            [obstructed_bfs_map[x][y] for x, y in game.tavern_locs], \
            [bfs_map[x][y] for x, y in game.mine_locs], \
            [obstructed_bfs_map[x][y] for x, y in game.mine_locs]))
        return self.db.fetchone()[0]
    
    def _insertMinesToDB(self, game, turn_id, hero_ids):
        for mine_number, mine_pos in enumerate(game.mine_locs):
            owner_of_mine = game.board.tile(mine_pos).heroId
            hero_id = hero_ids[owner_of_mine-1] if owner_of_mine is not None else None
            
            self.db.execute(
                "INSERT INTO Mines "
                "    (gameId, turnId, mineNumber, pos, heroId) "
                "VALUES (%(gameId)s, %(turnId)s, %(mineNumber)s, %(pos)s, %(heroId)s);", 
                {"gameId": game.gameId, "turnId": turn_id, "mineNumber": mine_number+1, \
                "pos": list(mine_pos), "heroId": hero_id})

if __name__ == "__main__":
    inserter = Inserter()
    game_file = open("logs/log1.log")
    inserter.insertGame(game_file.readlines())
    game_file.close()

    
        
        
        
        