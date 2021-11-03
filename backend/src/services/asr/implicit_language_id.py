# Middleware that does language ID from ASR outputs
# The idea for this is that we can score the output of different languages'
# ASR and determine the most likely language.

import time

from .interface import (
    SpeechRecognitionRequest,
    SpeechRecognitionResponse,
    LanguageIdRequest,
    LanguageIdResponse,
)
from .asr_middleware import AsrMiddleware

# Approximate relative length of a written corpus
# These are taken by comparing the length of the UN Declaration of Human Rights and
# comparing the length to English. (http://research.ics.aalto.fi/cog/data/udhr/)
# I assume that it takes someone the same amount of time to read this in each language,
# because the content is the same and all languages deliver content at the same rate.
LENGTH_CONSTANTS = {
    "en-US": 1,
    "zh": 0.574,
    "es-ES": 1.143,
    "pt-BR": 1.103,
}


class ImplicitLanguageID(AsrMiddleware):
    """
    Provider that does ASR, then determines language by scoring the ASR outputs.
    This removes the need for an explicit language id module.
    """

    def __init__(
        self,
        providers,
        config,
        logger,
        start_time,
        callback_fn,
        language_id_callback_fn=None,
    ):
        super().__init__(
            providers, config, logger, start_time, callback_fn, language_id_callback_fn
        )

        # This model keeps track of a score from ASR, where greater is better. It can be confidence
        # from a ML model, ratio of tokens to <unk> tokens, or length of utterances etc.
        # The best_response will either be the output from one of the active ASR systems
        # or the most recent complete sentence from one of the ASR systems
        self.user_language = config.language
        self.best_score = 0

    def intermediate_callback(
        self, request: SpeechRecognitionRequest, response: SpeechRecognitionResponse
    ):
        """
        Middleware that only returns ASR output in the user's language,
        but also watches for language switches
        """

        # Check if we should swap language
        # This happens if the new language score would be better than our current one
        # and the person has been speaking for at least 1 second.
        current_score = ImplicitLanguageID._score_result(request, response)
        if current_score > self.best_score:
            self.best_score = current_score

            if (
                self.user_language != response.language
                and time.time() - response.utterance_length > 1.0
                and len(response.transcript) > 2
            ):
                self.language_id_callback_fn(
                    LanguageIdRequest(
                        session_id=request.session_id,
                    ),
                    LanguageIdResponse(
                        detected_language=response.language,
                    ),
                )

        # Reset transcript when we get is_final, for currency.
        if response.is_final and response.language == self.user_language:
            self.best_score = current_score

        # Suppress output from ASR systems in other languages
        if response.language == self.user_language:
            self.callback_fn(request, response)

    @staticmethod
    def _score_result(
        request: SpeechRecognitionRequest, response: SpeechRecognitionResponse
    ):
        """
        Measure the rate of words from the ASR system.
        A correctly matched ASR system will have a higher rate.
        """
        return (
            len(response.transcript)
            / LENGTH_CONSTANTS[response.language]
            / (
                response.utterance_length + 1
            )  # add a second to penalize short utterances
        )
