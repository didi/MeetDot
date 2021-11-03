import json
import os
import re
import time

import gevent
import gevent.lock
import websocket as ws

from ..interface import (
    SpeechRecognitionConfig,
    SpeechRecognitionRequest,
    SpeechRecognitionResponse,
)
from ..stream_asr import StreamAsr


class KaldiStreamAsr(StreamAsr):
    # SUPPORTED_LANGUAGES = ("en-US", "zh", "es-ES", "pt-BR")
    SUPPORTED_LANGUAGES = ("en-US", "zh")

    def __init__(
        self, config: SpeechRecognitionConfig, logger, start_time, callback_fn
    ):
        super(KaldiStreamAsr, self).__init__(config, logger, start_time, callback_fn)
        self.url = os.getenv("KALDI_URL")
        self.semaphore = gevent.lock.Semaphore()
        self.connect()
        self.got_final = False

    def connect(self):
        try:
            self.socket = ws.create_connection(self.url)
        except ConnectionRefusedError:
            raise ConnectionRefusedError(
                f"Could not connect to Kaldi ASR server at {self.url} - is it running?"
            )
        with self.semaphore:
            self.socket.send(json.dumps({"config": self.config.to_dict()}))

    def run(self):
        if not self.socket.connected:
            self.connect()

        while True:
            data = self.socket.recv()
            current_time = time.time()

            if len(data) == 0:
                self.got_final = True

                break
            data = json.loads(data)

            if "text" in data:
                # Final response
                text = data["text"]
                is_final = True
            else:
                # Partial response
                text = data["partial"]
                is_final = False

            text = self.postprocess(text)

            if len(text) == 0:
                continue

            if self.utterance_start_time is None:
                self.utterance_start_time = current_time - self.start_time
            response = SpeechRecognitionResponse(
                transcript=text,
                utterance_start_time=self.utterance_start_time,
                utterance_length=current_time - self.utterance_start_time,
                is_final=is_final,
                language=self.config.language,
            )
            if is_final:
                # Reset the start time at the end of the utterance
                self.utterance_start_time = None

            self.callback_fn(self.last_request, response)

    def postprocess(self, text):
        # Remove filler words
        word_delimiter = "" if self.config.language == "zh" else " "
        filler_words = ("mhm", "uh", "um")
        text = word_delimiter.join(
            w for w in text.strip().split() if w not in filler_words
        )

        # Remove content in parenthesis: {}, <>, [], and ()
        text = re.sub(r"[<{\(\[].*?[\)\]>}]", "", text.strip())
        # Fix acronyms
        text = text.replace("._", ".")

        # Remove leading and trailing whitespace
        text = text.strip()

        if self.config.language == "zh":
            # Remove spaces, speaker ID in chinese
            text = text.replace("[SPK]", "")
            text = text.replace(" ", "")
        else:
            if text:
                text = text[0].capitalize() + text[1:]
            text = re.sub(r"\bi\b", "I", text)

        return text

    def __call__(self, request: SpeechRecognitionRequest) -> None:
        try:
            with self.semaphore:
                self.socket.send_binary(request.chunk)
        except BrokenPipeError:
            self.connect()
        self.last_request = request

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

    def wait_for_final(self, timeout_seconds=1.0):
        while not self.got_final:
            gevent.sleep(0.1)
