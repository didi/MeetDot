import time
from unittest import mock

import pytest

from services.asr import (
    SpeechRecognitionConfig,
    SpeechRecognitionService,
    SpeechRecognitionRequest,
)
from services.asr.language_id.language_id_config import LanguageIdConfig


asr_test_data = [
    ({"en-US": "kaldi"}, "en-US"),
    ({"zh": "kaldi"}, "zh"),
    ({"en-US": "wenet"}, "en-US"),
    ({"zh": "wenet"}, "zh"),
    (
        {"en-US": "google", "zh": "wenet", "pt-BR": "google"},
        "en-US",
    ),  # Test multiple providers
]


@pytest.mark.parametrize("providers,lang", asr_test_data)
def test_providers(providers, lang):
    """Test initializing each of the providers. We run each on a tiny chunk of data"""
    asr_config = SpeechRecognitionConfig(providers=providers, language=lang)
    request = SpeechRecognitionRequest(
        "session",
        "1234567890",
        end_utterance=False,
    )

    def has_data(req, res):
        pass

    asr_service = SpeechRecognitionService(
        asr_config, mock.Mock(), time.time(), has_data, None
    )
    asr_service(request)
    asr_service.terminate(wait_for_final=False)

    # We can't test for data returned because the callback isn't always called


middleware_test_data = [
    ({"en-US": "kaldi", "zh": "kaldi"}, "basic"),
    ({"en-US": "wenet", "zh": "wenet"}, "basic"),
    ({"en-US": "wenet", "zh": "wenet"}, "language_id"),
]


@pytest.mark.parametrize("providers,middleware_provider", middleware_test_data)
def test_middleware(providers, middleware_provider):
    language_id_config = LanguageIdConfig(enabled=False)
    asr_config = SpeechRecognitionConfig(
        providers=providers,
        middleware_provider=middleware_provider,
        language_id=language_id_config,
    )

    request = SpeechRecognitionRequest(
        "session",
        "1234567890",
        end_utterance=False,
    )

    def has_data(req, res):
        pass

    asr_service = SpeechRecognitionService(
        asr_config, mock.Mock(), time.time(), has_data, None
    )
    asr_service(request)
    asr_service.terminate(wait_for_final=False)
