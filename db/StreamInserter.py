import ast

from multiprocessing import Process

from Inserter import Inserter
from Streamer import Streamer

class StreamInserter():
    def __init__(self, hostname):
        self.hostname = hostname
    
    def start(self):
        already_streaming_game_ids = set()
        now_playing_streamer = Streamer(self.hostname + "/now-playing")
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
        inserter = Inserter()
        streamer = Streamer(self.hostname + "/events/" + game_id)
        inserter.insertGame(streamer.stream())

if __name__ == "__main__":
    stream_inserter = StreamInserter("http://vindinium.org")
    stream_inserter.start()
