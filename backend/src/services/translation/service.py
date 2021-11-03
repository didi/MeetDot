import asyncio
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
    ):
        self.config = config
        self.callback_fn = callback_fn
        self.logger = logger

        if config.provider in TranslationService.PROVIDERS:
            self.provider = TranslationService.PROVIDERS[config.provider](
                config, callback_fn, logger
            )
        else:
            raise ValueError(
                f"Unsupported translation provider {config.provider}, supported providers"
                + f" are {TranslationService.PROVIDERS}"
            )

    def __call__(self, request: TranslationRequest):
        self.provider(request, self.callback_fn)

    async def call(self, request: TranslationRequest) -> TranslationResponse:
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        def on_success(req: TranslationRequest, res: TranslationResponse):
            future.set_result(res)

        self.provider(request, on_success)
        await asyncio.wait_for(future, 2)

        return future.result()

    def end_session(self, session_id, wait_for_final=True):
        return self.provider.end_session(session_id, wait_for_final)
