import warnings

from .google_stream_asr import GoogleStreamAsr
from .iflytek_asr import IFlyTekAsr
from .interface import SpeechRecognitionRequest, LanguageIdRequest, LanguageIdResponse
from .kaldi import KaldiStreamAsr, KaldiHTTPAsr
from .language_id.language_id import LanguageDetector
from .wenet import WenetStreamAsr


class SpeechRecognitionService:
    PROVIDERS = {
        "google": GoogleStreamAsr,
        "wenet": WenetStreamAsr,
        "kaldi": KaldiStreamAsr,
        "iFlytek": IFlyTekAsr,
        "kaldi HTTP (en, zh)": KaldiHTTPAsr,
        "iFlytek": IFlyTekAsr,
    }

    def __init__(self, config, logger, callback_fn, language_id_callback_fn):
        self.logger = logger
        self.config = config
        self.language = config.language
        self.language_id_callback_fn = language_id_callback_fn

        if config.language_id.enabled:
            self.language_detector = LanguageDetector(config, logger)
        else:
            self.language_detector = None

        if config.provider in SpeechRecognitionService.PROVIDERS:
            if (
                (
                    config.provider == "kaldi"
                    and self.language not in KaldiStreamAsr.SUPPORTED_LANGUAGES
                )
                or (
                    config.provider == "kaldi HTTP (en, zh)"
                    and self.language not in KaldiHTTPAsr.SUPPORTED_LANGUAGES
                )
                or (
                    config.provider == "wenet"
                    and self.language not in WenetStreamAsr.SUPPORTED_LANGUAGES
                )
            ):
                logger.info(
                    f"Unsupported language ({self.language}) for {config.provider}, "
                    + "falling back to Google ASR"
                )
                config.provider = "google"
            self.provider = SpeechRecognitionService.PROVIDERS[config.provider](
                config, logger, callback_fn
            )
        else:
            raise ValueError(
                f"Unsupported speech recognition provider {config.provider}, installed providers"
                + f"are {SpeechRecognitionService.PROVIDERS}"
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
            self.provider.detected_language = language
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

    def terminate(self, wait_for_final=True):
        if self.language_detector is not None:
            self.language_detector.terminate()
        return self.provider.terminate(wait_for_final=wait_for_final)

    def end_utterance(self):
        if self.language_detector is not None:
            self.language_detector.terminate()
        return self.provider.end_utterance()

    def wait_for_final(self):
        return self.provider.wait_for_final()
