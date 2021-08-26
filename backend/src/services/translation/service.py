from typing import Any, Callable

from utils import start_thread

from .didi_translator import DiDiTranslator
from .google_translator import GoogleTranslator
from .interface import TranslationConfig, TranslationRequest, TranslationResponse


class TranslationService:
    PROVIDERS = {"google": GoogleTranslator, "didi": DiDiTranslator}

    def __init__(
        self,
        config: TranslationConfig,
        callback_fn: Callable[[TranslationRequest, TranslationResponse], Any],
        logger,
        start_background_task=start_thread,
    ):
        self.config = config
        self.callback_fn = callback_fn
        self.logger = logger
        self.start_background_task = start_background_task

        if config.provider in TranslationService.PROVIDERS:
            self.provider = TranslationService.PROVIDERS[config.provider](
                config, callback_fn, logger, start_background_task
            )
        else:
            raise ValueError(
                f"Unsupported translation provider {config.provider}, supported providers"
                + f" are {TranslationService.PROVIDERS}"
            )

    def __call__(self, request: TranslationRequest) -> TranslationResponse:
        return self.provider(request)

    def end_session(self, session_id, wait_for_final=True):
        return self.provider.end_session(session_id, wait_for_final)
