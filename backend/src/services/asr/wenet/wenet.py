import json
import os
import re
import time

import gevent
import gevent.lock
import websocket as ws

from services.asr.interface import (
    SpeechRecognitionConfig,
    SpeechRecognitionRequest,
    SpeechRecognitionResponse,
)
from services.asr.stream_asr import StreamAsr


class WenetStreamAsr(StreamAsr):
    SUPPORTED_LANGUAGES = ("en-US", "zh", "es-ES")

    def __init__(
        self, config: SpeechRecognitionConfig, logger, start_time, callback_fn
    ):
        super(WenetStreamAsr, self).__init__(config, logger, start_time, callback_fn)
        self.url = os.getenv("WENET_URL")
        self.semaphore = gevent.lock.Semaphore()
        self.connect(config.language)
        self.got_final = False

    def connect(self, language):
        try:
            self.socket = ws.create_connection(self.url)
        except ConnectionRefusedError:
            raise ConnectionRefusedError(
                f"Could not connect to Wenet ASR server at {self.url} - is it running?"
            )
        with self.semaphore:
            self.socket.send(
                json.dumps(
                    {
                        "signal": "start",
                        "nbest": 1,
                        "continuous_decoding": True,
                        "language": language,
                    }
                )
            )

    def run(self):
        while True:
            data = self.socket.recv()
            current_time = time.time()

            data = json.loads(data)
            if data["type"] in ("partial_result", "final_result"):
                nbest = json.loads(data["nbest"])
                if len(nbest) == 0:
                    continue
                text = nbest[0]["sentence"]
                is_final = data["type"] == "final_result"
            elif data["type"] == "speech_end":
                self.got_final = True
                break
            else:
                continue

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
        if self.config.language == "zh":
            for character in ("呃", "嗯", "啊", "哎"):
                text = text.replace(character, "")
        elif self.config.language == "en-US":
            # Remove filler words
            word_delimiter = " "
            filler_words = ("mhm", "uh", "um", "ah")
            text = word_delimiter.join(
                w for w in text.strip().split() if w not in filler_words
            )

            # Remove content in parenthesis: {}, <>, [], and ()
            text = re.sub(r"[<{\(\[].*?[\)\]>}]", "", text.strip())
            # Fix acronyms
            text = text.replace("._", ".")

            # Remove leading and trailing whitespace
            text = text.strip()

            if text:
                text = text[0].capitalize() + text[1:]
            text = re.sub(r"\bi\b", "I", text)

        return text

    def __call__(self, request: SpeechRecognitionRequest) -> None:
        with self.semaphore:
            self.socket.send_binary(request.chunk)
        self.last_request = request

    def end_utterance(self):
        # Send special end of stream message
        self.got_final = False
        with self.semaphore:
            self.socket.send(
                json.dumps(
                    {
                        "signal": "end",
                    }
                )
            )

    def terminate(self, wait_for_final=True):
        self.end_utterance()

        if wait_for_final:
            self.wait_for_final()

        self.socket.close()

    def wait_for_final(self, timeout_seconds=1.0):
        while not self.got_final:
            gevent.sleep(0.1)
