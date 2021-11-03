import base64
import gevent
import os
import time

from ..interface import (
    SpeechRecognitionConfig,
    SpeechRecognitionRequest,
    SpeechRecognitionResponse,
)
from ..stream_asr import StreamAsr
import requests


class KaldiHTTPAsr(StreamAsr):
    SUPPORTED_LANGUAGES = ("en-US", "zh")
    POLLING_INTERVAL = 0.1

    def __init__(
        self, config: SpeechRecognitionConfig, logger, start_time, callback_fn
    ):
        super(KaldiHTTPAsr, self).__init__(config, logger, start_time, callback_fn)
        self.base_url: str = os.getenv("KALDI_HTTP_URL", "")
        self.kaldi_session_id = None
        api_key = os.getenv("KALDI_HTTP_API_KEY", "")
        self.headers = {"Content-Type": "application/json", "access_token": api_key}
        self.index = 0
        self.completed_utterances = set()
        self.last_utterance = {}
        self.connect()

    def connect(self):
        request_url = "/".join([self.base_url, "session"])
        request_dict = {
            "language_code": self.config.language,
        }
        response = requests.post(
            url=request_url, headers=self.headers, json=request_dict
        )

        if response.status_code != 200:
            raise Exception(f"Error connecting to Kaldi: {response.status_code}")

        response = response.json()

        if response["error_code"] != 0:
            raise Exception(
                f"Kaldi ASR could not create session: {response['error_msg']}"
            )

        self.kaldi_session_id = response["session_id"]

    def run(self):
        while True:
            request_url = "/".join([self.base_url, "transcript"])
            request_dict = {"session_id": self.kaldi_session_id}

            api_response = requests.get(
                url=request_url, headers=self.headers, params=request_dict
            )

            if api_response.status_code != 200:
                raise Exception(
                    f"Error connecting to Kaldi: {api_response.status_code}"
                )
            api_response = api_response.json()

            if api_response["error_code"] != 0:
                break

            data = api_response["data"]

            for utterance in data:
                utterance_id = utterance["utterance_id"]

                # Disregard already finished utterances
                if utterance_id in self.completed_utterances:
                    continue

                # Add completed utterance
                if utterance["is_final"]:
                    self.completed_utterances.add(utterance_id)
                    self.last_utterance.pop(utterance_id)

                self.last_utterance.setdefault(utterance_id, (-1, ""))

                if (
                    self.last_utterance[utterance_id][0] < utterance["last_index"]
                    and self.last_utterance[utterance_id][1] != utterance["transcript"]
                ):
                    self.last_utterance[utterance_id] = (
                        utterance["last_index"],
                        utterance["transcript"],
                    )
                    if self.utterance_start_time is None:
                        self.utterance_start_time = time.time() - self.start_time
                    response = SpeechRecognitionResponse(
                        transcript=utterance["transcript"],
                        utterance_start_time=self.utterance_start_time,
                        is_final=utterance["is_final"],
                        language=self.detected_language,
                    )
                    if response.is_final:
                        # Reset the start time at the end of the utterance
                        self.utterance_start_time = None
                    self.callback_fn(self.last_request, response)
            gevent.sleep(KaldiHTTPAsr.POLLING_INTERVAL)

    def __call__(self, request: SpeechRecognitionRequest) -> None:
        self.last_request = request
        request_url = "/".join([self.base_url, "audio"])
        data = base64.b64encode(request.chunk).decode("utf-8")
        request_dict = {
            "session_id": self.kaldi_session_id,
            "data": data,
            "index": self.index,
            "timestamp": time.time(),
        }
        response = requests.post(
            url=request_url, headers=self.headers, json=request_dict
        )

        if response.status_code != 200:
            raise Exception(
                f"Error connecting to Kaldi: {response.status_code} {response.txt}"
            )

        self.index += 1

    def terminate(self, wait_for_final=True):
        request_url = "/".join([self.base_url, "session"])
        request_dict = {
            "session_id": self.kaldi_session_id,
        }
        response = requests.delete(
            url=request_url, headers=self.headers, json=request_dict
        )

        if response.status_code != 200:
            raise Exception(
                f"Error connecting to Kaldi: {response.status_code} {response.txt}"
            )
