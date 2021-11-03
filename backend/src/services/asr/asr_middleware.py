# Middleware that combines the results of multiple ASR providers in different languages
from copy import copy
from typing import Dict, Type

import gevent

from .stream_asr import StreamAsr
from .interface import (
    SpeechRecognitionRequest,
    SpeechRecognitionResponse,
    SpeechRecognitionConfig,
    LanguageIdRequest,
    LanguageIdResponse,
)
from utils import start_thread


class AsrMiddleware(StreamAsr):
    def __init__(
        self,
        providers: Dict[str, Type[StreamAsr]],
        config: SpeechRecognitionConfig,
        logger,
        start_time,
        callback_fn,
        language_id_callback_fn=None,
    ):
        super().__init__(config, logger, start_time, callback_fn)
        self.language_id_callback_fn = language_id_callback_fn

        # Create ASR providers for each language
        self.providers = []
        for lang, provider in providers.items():
            new_config = copy(config)
            new_config.language = lang
            self.providers.append(
                provider(new_config, logger, start_time, self.intermediate_callback)
            )

    def __call__(self, request: SpeechRecognitionRequest) -> None:
        """Send audio chunks to each provider"""
        for p in self.providers:
            p(request)

    def intermediate_callback(
        self, req: SpeechRecognitionRequest, res: SpeechRecognitionResponse
    ):
        """
        This function acts as middleware and is called on all SpeechRecognitionResponses.

        This function can either return nothing (ASR filtering) or can call
        `self.callback(req, res)` to pass good ASR results to the front-end.
        It can optionally call `self.language_id_callback_fn` if doing language ID as well.
        """

        # Base class returns all ASR outputs to the frontend
        self.callback_fn(req, res)

    def run(self):
        for p in self.providers:
            start_thread(p.run)

    def terminate(self, wait_for_final=True):
        for p in self.providers:
            p.terminate(wait_for_final)

    def end_utterance(self):
        for p in self.providers:
            p.end_utterance()

    def wait_for_final(self, timeout_seconds=1.0):
        while not all(p.got_final for p in self.providers):
            gevent.sleep(0.1)
