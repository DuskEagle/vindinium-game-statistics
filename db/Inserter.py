import sys
sys.path.insert(0, "../game")

import ast
import datetime
import logging
import numpy as np
import psycopg2 as psycopg
from multiprocessing import Lock
from psycopg2.extras import Json

from game import Game

class Inserter():
    insert_user_lock = Lock()
    
    def __init__(self, dbname="vindinium", dbuser="postgres"):
        self.connection = psycopg.connect("dbname=" + dbname + " user=" + dbuser)
        self.db = self.connection.cursor()
        self.logger = self.configureLogger(logging.DEBUG)
        
    def configureLogger(self, log_level):
        logger = logging.getLogger("Inserter")
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(stdout_handler)
        logger.setLevel(log_level)
        return logger
    
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
    
    def insertTurn(self, turn_string, old_game):
        """ Insert turn represented by turn_string into database. """
        
        state = Inserter._parseJson(turn_string)
        game = Game(state, False)
        if old_game is None:
            freshly_dead_heroes = []
        else:
            freshly_dead_heroes = Game.getFreshlyDeadHeroes(old_game, game)
        
        turn_id = self._insertTurnToDB(game, state)
        
        hero_ids = []
        for hero in game.heroes:
            hero_ids.append(self._insertHeroToDB(game, hero, turn_id, hero in freshly_dead_heroes))
        
        self._insertMinesToDB(game, turn_id, hero_ids)
        
        return game
    
    def _insertGame(self, first_turn_string):
        state = Inserter._parseJson(first_turn_string)
        game = Game(state, False)
        logging.info("Inserting " + game.gameId + " to database.")
        
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
        if game.finished:
            self.db.execute(
                "UPDATE GAMES "
                "    SET finished = TRUE "
                "WHERE gameId = %s;",
                (game.gameId,))
        
        self.db.execute(
            "INSERT INTO Turns "
            "    (gameId, turn, rawJSON, previousTurnId) "
            "VALUES (%(gameId)s, %(turn)s, %(rawJSON)s, "
            "    (SELECT t.id FROM Turns t "
            "    LEFT JOIN Turns t_later "
            "        ON t_later.gameId = t.gameid "
            "        AND t_later.previousTurnId = t.id "
            "    WHERE t.gameId = %(gameId)s "
            "        AND t_later.id IS NULL)) "
            "RETURNING id;",
            {"gameId": game.gameId, "turn": game.turn, "rawJSON": Json(state)})
        return self.db.fetchone()[0]
        
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
                "    (gameId, turnId, mineNumber, pos, heroId, previousMineId) "
                "VALUES (%(gameId)s, %(turnId)s, %(mineNumber)s, %(pos)s, %(heroId)s, "
                "    (SELECT m.id FROM Mines m "
                "    LEFT JOIN Mines m_later "
                "        ON m_later.gameId = m.gameId "
                "        AND m_later.mineNumber = m.mineNumber "
                "        AND m_later.previousMineId = m.id "
                "    WHERE m.gameId = %(gameId)s "
                "    AND m.mineNumber = %(mineNumber)s "
                "    AND m_later.id IS NULL));",
                {"gameId": game.gameId, "turnId": turn_id, "mineNumber": mine_number+1, \
                "pos": list(mine_pos), "heroId": hero_id})



if __name__ == "__main__":
    inserter = Inserter()
    game_file = open("logs/log1.log")
    inserter.insertGame(game_file.readlines())
    game_file.close()

    
        
        
        
        