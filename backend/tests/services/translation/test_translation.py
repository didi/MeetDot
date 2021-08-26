from unittest import mock

import pytest
from services.translation import (
    TranslationConfig,
    TranslationRequest,
    TranslationResponse,
    TranslationService,
)

translation_test_data = [
    # Test same language returns same string
    ("google", "Hello test", "en-US", "en-US", "Hello test", None),
    ("didi", "Hello test", "en-US", "en-US", "Hello test", None),
    ("google", "你好", "zh", "zh", "你好", None),
    # Test some real outputs
    ("google", "Hello", "en-US", "zh", ("您好", "你好"), None),
    ("google", "Hello", "en-US", "es-ES", "Hola", None),
    (
        "google",
        "Buenos días damas y caballeros",
        "es-ES",
        "en-US",
        "Good morning ladies and gentlemen",
        None,
    ),
    ("didi", "Hello", "en-US", "zh", "你好", False),
]


@pytest.mark.parametrize(
    "provider,s,source_lang,target_lang,expected_translation,expected_raw_translation",
    translation_test_data,
)
def test_translation(
    provider,
    s,
    source_lang,
    target_lang,
    expected_translation,
    expected_raw_translation,
):
    config = TranslationConfig(provider=provider)
    response_holder = []

    def on_translation(req, res):
        response_holder.append(res)

    translator = TranslationService(
        config, logger=mock.Mock(), callback_fn=on_translation
    )
    session_id = "test"
    request = TranslationRequest(
        session_id=session_id,
        message_id=0,
        text=s,
        source_language=source_lang,
        target_language=target_lang,
    )
    translator(request)
    translator.end_session(session_id, wait_for_final=True)
    response = response_holder[0]

    if type(expected_translation) == tuple:
        assert response.translation in expected_translation
    else:
        assert response.translation == expected_translation
    if expected_raw_translation:
        assert response.raw_translation == expected_raw_translation
