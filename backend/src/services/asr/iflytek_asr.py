"""
iflytek stream ASR service class (using WebSocket)
"""
import gevent
import os

from .interface import (
    SpeechRecognitionConfig,
    SpeechRecognitionRequest,
    SpeechRecognitionResponse,
)
from .stream_asr import StreamAsr
from ..tokenizer import Tokenizer

import sys
import hashlib
from hashlib import sha1
import hmac
import base64
import json
import time
from websocket import create_connection
import websocket
from urllib.parse import quote
import logging
import queue
import re

"""
If you want to use iFlytek ASR service, copy your credentials into .env file under repo dir.
IFLYTEK_URL="XXX"
IFLYTEK_API_ID="XXX"
IFLYTEK_API_KEY="XXX"

"""

# iFlytek ASR use different language codes, mapping languages in our systems to iflytek's.
LANGUAGE_CODE_MAPPING = {"zh": "cn", "en-US": "en"}


class IFlyTekAsr(StreamAsr):
    SUPPORTED_LANGUAGES = ("en-US", "zh")
    POLLING_INTERVAL = 0.1  # seconds

    def __init__(self, config: SpeechRecognitionConfig, logger, callback_fn):
        super(IFlyTekAsr, self).__init__(config, logger, callback_fn)
        self.start_time = time.time()
        self.base_url: str = os.getenv("IFLYTEK_URL", "")
        self.api_id = os.getenv("IFLYTEK_API_ID", "")
        self.api_key = os.getenv("IFLYTEK_API_KEY", "")

        self.init_timestamp = str(int(time.time()))
        self.pd = "edu"  # ASR domain
        self.end_tag = '{"end": true}'
        self.got_final = False

        self.signa = self._get_signature()
        self.lang_code = LANGUAGE_CODE_MAPPING[self.user_language]
        # TODO: self.tokenizer does not support on-the-fly language switch.
        self.tokenizer = Tokenizer(lang=self.user_language)

        self.semaphore = gevent.lock.Semaphore()
        self.connect()

    def connect(self):
        try:
            self.ws = create_connection(
                self.base_url
                + "?appid="
                + self.api_id
                + "&ts="
                + self.init_timestamp
                + "&signa="
                + quote(self.signa)
                + "&lang="
                + quote(self.lang_code)
            )
        except ConnectionRefusedError:
            raise ConnectionRefusedError(
                f"Could not connect to iflytek ASR server at {self.base_url} - is it running?"
            )
        with self.semaphore:
            self.ws.send("")

    def _get_signature(self):
        tt = (self.api_id + self.init_timestamp).encode("utf-8")
        md5 = hashlib.md5()
        md5.update(tt)
        baseString = md5.hexdigest()
        baseString = bytes(baseString, encoding="utf-8")
        apiKey = self.api_key.encode("utf-8")
        signa = hmac.new(apiKey, baseString, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = str(signa, "utf-8")

        return signa

    def run(self):
        if not self.ws.connected:
            self.connect()

        while self.ws.connected:
            try:
                api_response = str(self.ws.recv())
            except websocket.WebSocketConnectionClosedException:
                print("receive result end")
                break

            if len(api_response) == 0:
                self.got_final = True

                break
            api_response = json.loads(api_response)
            response_code = int(api_response["code"])

            if response_code != 0:
                self.logger.error(f"ASR Response Error code: {response_code}")
                continue

            data = api_response["data"]
            if api_response["action"] == "result":
                data = json.loads(data)
                pure_words_list = [
                    i["cw"][0]["w"] for i in data["cn"]["st"]["rt"][0]["ws"]
                ]
                # 0-final result; 1-intermediate result
                utterance_is_final = int(data["cn"]["st"]["type"]) == 0
                if utterance_is_final:
                    self.got_final = True

                response = SpeechRecognitionResponse(
                    transcript=self._build_transcript(tokens=pure_words_list),
                    relative_time_offset=time.time() - self.start_time,
                    is_final=utterance_is_final,
                    language=LANGUAGE_CODE_MAPPING[self.detected_language],
                )
                self.callback_fn(self.last_request, response)

            gevent.sleep(IFlyTekAsr.POLLING_INTERVAL)

    def __call__(self, request: SpeechRecognitionRequest) -> None:
        self.last_request = request
        data = request.chunk
        self._send_chunk(data)

    def end_utterance(self):
        # Send special end of stream message
        self._send_chunk(bytes(self.end_tag.encode("utf-8")))

    def terminate(self, wait_for_final=True):
        self.end_utterance()
        if wait_for_final:
            self.wait_for_final()
        self.ws.close()

    def wait_for_final(self, timeout_seconds=2.0):
        """
        After closing, wait until the final response is sent, up to a timeout
        """
        q = queue.Queue()
        original_callback = self.callback_fn

        def wrapped_callback(request, response):
            if response.is_final:
                q.put(response)
            original_callback(request, response)

        self.callback_fn = wrapped_callback
        try:
            final_response = q.get(timeout=timeout_seconds)
        except queue.Empty:
            final_response = SpeechRecognitionResponse(
                transcript="",
                relative_time_offset=0,
                is_final=True,
                language=self.detected_language,
            )
        self.callback_fn = original_callback

        while not self.got_final:
            gevent.sleep(0.01)
        return final_response

    def _build_transcript(self, tokens: list):
        raw_transcript = self.tokenizer.detokenize(tokens)
        transcript = self.postprocess(raw_transcript)
        return transcript

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

    def _send_chunk(self, data):
        try:
            self.ws.send(data)
        except websocket.WebSocketConnectionClosedException:
            self.logger.warning(
                "WebSocketConnectionClosedException: socket is already closed."
            )
