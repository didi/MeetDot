import json
import os

import gevent.lock
import websocket as ws
from services.asr.interface import SpeechRecognitionConfig


class LanguageIdClient:
    def __init__(self, config: SpeechRecognitionConfig, logger):
        self.active = True
        self.asr_config = config
        self.config = config.language_id
        self.language = config.language
        self.url = os.getenv("LANGUAGE_ID_URL")
        self.semaphore = gevent.lock.Semaphore()
        self.connect()

    def connect(self):
        try:
            self.socket = ws.create_connection(self.url)
        except ConnectionRefusedError:
            raise ConnectionRefusedError(
                f"Could not connect to language ID server at {self.url} - is it running?"
            )
        with self.semaphore:
            self.socket.send(
                json.dumps(
                    {
                        "config": self.config.to_dict(),
                        "language": self.language,
                        "sample_rate_hertz": self.asr_config.sample_rate_hertz,
                        "chunk_size": self.asr_config.chunk_size,
                    }
                )
            )

    def run(self, update_language_fn):
        if not self.socket.connected:
            self.connect()

        while True:
            data = self.socket.recv()

            if len(data) == 0:
                self.got_final = True
                break

            data = json.loads(data)
            self.language = data["detected_language"]
            update_language_fn(self.session_id, self.language)

    def end_utterance(self):
        # Send special end of stream message
        self.got_final = False
        with self.semaphore:
            self.socket.send('{"eof" : 1}')

    def terminate(self, wait_for_final=True):
        self.end_utterance()

        if wait_for_final:
            self.wait_for_final()

        self.socket.close()

    def __call__(self, session_id, chunk):
        self.session_id = session_id
        try:
            with self.semaphore:
                self.socket.send_binary(chunk)
        except BrokenPipeError:
            self.connect()

    def wait_for_final(self, timeout_seconds=1.0):
        while not self.got_final:
            gevent.sleep(0.1)
