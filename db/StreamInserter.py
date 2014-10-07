import ast
import logging as _logging
import sys

from multiprocessing import Process

from Inserter import Inserter
from Streamer import Streamer

class StreamInserter():
    def __init__(self, hostname, database_name, database_user, logger=_logging.getLogger("StreamInserter")):
        self.hostname = hostname
        self.database_name = database_name
        self.database_user = database_user
        self.logger = logger
    
    def start(self):
        already_streaming_game_ids = set()
        now_playing_streamer = Streamer(self.hostname + "/now-playing", self.logger)
        for data in now_playing_streamer.stream():
            game_ids = set(ast.literal_eval(data))
            new_game_ids = game_ids - already_streaming_game_ids
            for game_id in new_game_ids:
                self.startGameStream(game_id)
            already_streaming_game_ids.update(game_ids)
    
    def startGameStream(self, game_id):
        process = Process(target=self._runGameStream, args=(game_id,))
        process.start()
    
    def _runGameStream(self, game_id):
        inserter = Inserter(self.database_name, self.database_user, self.logger)
        streamer = Streamer(self.hostname + "/events/" + game_id)
        inserter.insertGame(streamer.stream())

if __name__ == "__main__":
    
    def configureLogger(log_level):
        logger = _logging.getLogger("Global")
        stdout_handler = _logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(_logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(stdout_handler)
        logger.setLevel(log_level)
        return logger
    
    num_args = len(sys.argv)
    if num_args < 3:
        print("Usage: %s <database-name> <database-user> {hostname} {logging_level}" % (sys.argv[0]))
    
    database_name = sys.argv[1]
    database_user = sys.argv[2]
    if num_args >= 4:
        hostname = sys.argv[3]
    else:
        hostname = "http://vindinium.org/"
    
    if num_args >= 5:
        logging_level = getattr(_logging, sys.argv[4].upper(), None)
        if not isinstance(logging_level, int):
            print("logging_level should be one of \"DEBUG\", \"INFO\", \"WARN\", \"ERROR\", \"CRITICAL\".")
    else:
        logging_level = _logging.INFO
    logger = configureLogger(logging_level)
    
    stream_inserter = StreamInserter(hostname, database_name, database_user, logger)
    stream_inserter.start()
