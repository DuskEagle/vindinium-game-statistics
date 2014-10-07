import logging as _logging
import requests

class Streamer():
    
    def __init__(self, url, logger=_logging.getLogger("Streamer")):
        self.url = url
        req = requests.Request("GET", self.url).prepare()
        self.connection = requests.Session().send(req, stream=True)
        self.logger = logger
    
    def stream(self):
        """ Returns one line of stream data from URL. Waits if no line is on the
        stream. """
        while True:
            data = ""
            for char in self.connection.iter_content(decode_unicode=True):
                if not char:
                    continue
                if len(data) > 10000:
                    raise StreamerError("Stream data from " + self.url + " is too long!")
                
                if char != "\n":
                    data += char
                elif len(data) > 0:
                    break
            else:
                # If the session finished, this generator function shout return
                # StopIteration (which we do by breaking out of the while loop,
                # allowing the function to end).
                break
            yield data.lstrip("data: ")

class StreamerError(RuntimeError):
    pass


if __name__ == "__main__":
    s = Streamer("http://vindinium.org/events/3c46uy5r")
    #s = Streamer("http://vindinium.org/now-playing")
    for line in s.stream():
        print(line)
    #while True:
        #print(s.stream())
        
