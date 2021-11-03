from collections import defaultdict
from typing import Type
import warnings

from .stream_asr import StreamAsr
from .google_stream_asr import GoogleStreamAsr
from .iflytek_asr import IFlyTekAsr
from .interface import SpeechRecognitionRequest, LanguageIdRequest, LanguageIdResponse
from .kaldi import KaldiStreamAsr, KaldiHTTPAsr
from .language_id.client import LanguageIdClient
from .wenet import WenetStreamAsr
from .asr_middleware import AsrMiddleware
from .implicit_language_id import ImplicitLanguageID


class SpeechRecognitionService:
    PROVIDERS = {
        "google": GoogleStreamAsr,
        "wenet": WenetStreamAsr,
        "kaldi": KaldiStreamAsr,
        "iFlytek": IFlyTekAsr,
        "kaldi HTTP (en, zh)": KaldiHTTPAsr,
    }
    MIDDLEWARES = {
        "basic": AsrMiddleware,  # transparent middleware that does nothing
        "language_id": ImplicitLanguageID,  # do language id with asr outputs
    }

    @classmethod
    def supported_languages_to_providers(cls):
        languages_to_providers = defaultdict(list)
        for provider_name, provider_class in cls.PROVIDERS.items():
            for lang in provider_class.SUPPORTED_LANGUAGES:
                languages_to_providers[lang].append(provider_name)
        return languages_to_providers

    def __init__(
        self, config, logger, start_time, callback_fn, language_id_callback_fn
    ):
        self.logger = logger
        self.config = config
        self.start_time = start_time
        self.utterance_start_time = None
        self.language_id_callback_fn = language_id_callback_fn

        if config.language_id.enabled and config.middleware_provider is None:
            self.language_detector = LanguageIdClient(config, logger)
        else:
            self.language_detector = None

        for lang, provider in config.providers.items():
            if not provider:
                continue
            provider_class = SpeechRecognitionService.PROVIDERS.get(provider)
            if not provider_class:
                raise ValueError(
                    f"Unsupported speech recognition provider {provider}, installed providers"
                    + f"are {SpeechRecognitionService.PROVIDERS}"
                )
            if lang not in provider_class.SUPPORTED_LANGUAGES:
                raise ValueError(
                    f"{provider} does not support language: {lang}, supported_languages are"
                    + f"are {provider_class.SUPPORTED_LANGUAGES}"
                )

        if config.middleware_provider is None:
            provider_class = SpeechRecognitionService.PROVIDERS[
                config.providers[config.language]
            ]
            self.provider = provider_class(config, logger, start_time, callback_fn)
        else:
            providers = {
                lang: SpeechRecognitionService.PROVIDERS[provider_str]
                for lang, provider_str in config.providers.items()
            }
            self.provider = SpeechRecognitionService.MIDDLEWARES[
                config.middleware_provider
            ](
                providers,
                config,
                logger,
                start_time,
                callback_fn,
                language_id_callback_fn,
            )

    def __call__(self, request: SpeechRecognitionRequest):
        if self.language_detector is not None:
            self.language_detector(request.session_id, request.chunk)
        output = self.provider(request)
        if request.end_utterance:
            self.end_utterance()
        return output

    def run(self):
        return self.provider.run()

    def run_language_detect(self):
        def update_language(session_id, language):
            self.language_id_callback_fn(
                LanguageIdRequest(
                    session_id=session_id,
                ),
                LanguageIdResponse(
                    detected_language=language,
                ),
            )

        if self.language_detector is not None:
            return self.language_detector.run(update_language)

    def accept_new_language(self, new_language: str):
        """
        The combined ASR provider doesn't restart when the user accepts
        a new ASR language, so we need to notify it somehow
        """
        if self.config.middleware_provider is not None:
            self.provider.user_language = new_language

    def terminate(self, wait_for_final=True):
        if self.language_detector is not None:
            self.language_detector.terminate(wait_for_final=wait_for_final)
        return self.provider.terminate(wait_for_final=wait_for_final)

    def end_utterance(self):
        if self.language_detector is not None:
            self.language_detector.end_utterance()
        return self.provider.end_utterance()

    def wait_for_final(self):
        return self.provider.wait_for_final()
