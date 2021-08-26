from unittest import mock

import pytest
from services.post_translation import (
    PostTranslationConfig,
    PostTranslationRequest,
    PostTranslationService,
)


def setup_service(config):
    logger = mock.Mock()

    return PostTranslationService(config, logger)


@pytest.mark.parametrize(
    "translation,is_final,expected",
    [
        ("The quick brown fox jumped over", False, "The quick"),
        ("The quick brown fox jumped over", True, "The quick brown fox jumped over."),
        ("Hello", False, ""),
    ],
)
def test_post_translation_mask_k(translation, is_final, expected):
    """
    Test that post translation with mask-k works as expected
    """
    config = PostTranslationConfig(mask_k=4, translate_k=0)
    service = setup_service(config)

    request = PostTranslationRequest(
        session_id="test",
        message_id=0,
        translation=translation,
        is_final=is_final,
        # In order to activate mask-k we need to have different src and tgt languages
        original_language="en-dummy",
        language="en-US",
    )
    response = service(request)
    assert response.translation == expected


@pytest.mark.parametrize(
    "first,second,k",
    [
        ("The quick", "The quick brown fox", 4),
        ("", "Hello", 2),
    ],
)
def test_post_translation_translate_k(first, second, k):
    """
    Test that post translation with translate-k works as expected
    """
    config = PostTranslationConfig(mask_k=0, translate_k=k)
    service = setup_service(config)

    # First request should return first translation unchanged
    request = PostTranslationRequest(
        session_id="test",
        message_id=0,
        translation=first,
        is_final=False,
        # to activate translate-k we need to have different src and tgt languages
        original_language="en-dummy",
        language="en-US",
    )
    response = service(request)
    assert response.translation == first

    # Next requests should return first translation, not second

    for i in range(k - 1):
        request = PostTranslationRequest(
            session_id="test",
            message_id=i,
            translation=second,
            is_final=False,
            original_language="en-dummy",
            language="en-US",
        )
        response = service(request)
        assert response.translation == first

    # k-th request should return second translation
    request = PostTranslationRequest(
        session_id="test",
        message_id=10,
        translation=second,
        is_final=False,
        original_language="en-dummy",
        language="en-US",
    )
    response = service(request)
    assert response.translation == second


def test_translate_k_final_asr():
    config = PostTranslationConfig(mask_k=0, translate_k=3)
    service = setup_service(config)

    translations = [
        "first",
        "Second.",
        "third",
        "fourth",
    ]

    # First request should return first translation unchanged
    request = PostTranslationRequest(
        session_id="test",
        message_id=0,
        translation=translations[0],
        is_final=False,
        original_language="en-dummy",
        language="en-US",
    )
    response = service(request)
    assert response.translation == translations[0]

    # Second request should return the second translation,
    # because we are specifying it as a final request.
    request = PostTranslationRequest(
        session_id="test",
        message_id=1,
        translation=translations[1],
        is_final=True,
        original_language="en-dummy",
        language="en-US",
    )
    response = service(request)
    assert response.translation == translations[1]

    # Third request should return an empty translation,
    # because the previous final request cleared the cached translation.
    request = PostTranslationRequest(
        session_id="test",
        message_id=2,
        translation=translations[2],
        is_final=False,
        original_language="en-dummy",
        language="en-US",
    )
    response = service(request)
    assert response.translation == ""

    # Fourth request should return the fourth translation,
    # because we have reached first_request + k.
    request = PostTranslationRequest(
        session_id="test",
        message_id=3,
        translation=translations[3],
        is_final=False,
        original_language="en-dummy",
        language="en-US",
    )
    response = service(request)
    assert response.translation == translations[3]


def test_translate_k_final_asr_with_mask_k():
    config = PostTranslationConfig(translate_k=3, mask_k=1)
    service = setup_service(config)

    translations = [
        "first foo",
        "second foo",
        "third foo",
        "fourth foo",
        "fifth foo",
    ]

    # First request should return masked first translation.
    request = PostTranslationRequest(
        session_id="test",
        message_id=4,
        translation=translations[0],
        is_final=False,
        original_language="en-dummy",
        language="en-US",
    )
    response = service(request)
    assert response.translation == translations[0].split()[0]

    # Second request should return the unmasked second translation,
    # because we are specifying it as a final request.
    request = PostTranslationRequest(
        session_id="test",
        message_id=5,
        translation=translations[1],
        is_final=True,
        original_language="en-dummy",
        language="en-US",
    )
    response = service(request)
    assert response.translation == "Second foo."

    # Third request should return an empty translation,
    # because the previous final request cleared the cached translation.
    request = PostTranslationRequest(
        session_id="test",
        message_id=6,
        translation=translations[2],
        is_final=False,
        original_language="en-dummy",
        language="en-US",
    )
    response = service(request)
    assert response.translation == ""

    # Fourth request should return the masked fourth translation,
    # because we have reached first_request + k.
    request = PostTranslationRequest(
        session_id="test",
        message_id=7,
        translation=translations[3],
        is_final=False,
        original_language="en-dummy",
        language="en-US",
    )
    response = service(request)
    assert response.translation == translations[3].split()[0]

    # Fifth request should return the masked fourth translation,
    # because we just updated the translation on the previous request.
    request = PostTranslationRequest(
        session_id="test",
        message_id=8,
        translation=translations[4],
        is_final=False,
        original_language="en-dummy",
        language="en-US",
    )
    response = service(request)
    assert response.translation == translations[3].split()[0]


@pytest.mark.parametrize(
    "session1,session2,expected",
    [
        (
            ("The quick brown fox", "The quick brown fox jumps"),
            ("Lorem", "Lorem ipsum", "Lorem ipsum dolor"),
            ("The quick brown", "The quick brown fox", "", "Lorem", "Lorem ipsum"),
        ),
    ],
)
def test_post_translation_multi_session(session1, session2, expected):
    """
    Test that post translation handles multiple sessions properly
    """
    config = PostTranslationConfig(mask_k=1, translate_k=0)
    service = setup_service(config)
    i = 0

    for sentence in session1:
        request = PostTranslationRequest(
            session_id="session-1",
            message_id=i,
            translation=sentence,
            is_final=False,
            original_language="en-dummy",
            language="en-US",
        )
        response = service(request)
        assert response.translation == expected[i]
        i += 1

    for sentence in session2:
        request = PostTranslationRequest(
            session_id="session-2",
            message_id=i,
            translation=sentence,
            is_final=False,
            original_language="en-dummy",
            language="en-US",
        )
        response = service(request)
        assert response.translation == expected[i]
        i += 1


@pytest.mark.parametrize(
    "target_1,target_2,expected",
    [
        (
            ("en-US", ("The quick brown fox", "The quick brown fox jumps")),
            ("zh", ("你好", "你好我是", "你好我是一个人")),
            ("The quick brown", "The quick brown fox", "", "你好我", "你好我是一个"),
        ),
    ],
)
def test_mask_k_multi_language(target_1, target_2, expected):
    """
    Test that post-translation can handle a single session in multiple languages
    """
    config = PostTranslationConfig(mask_k=1, translate_k=0)
    service = setup_service(config)
    i = 0

    language, sentences = target_1

    for sentence in sentences:
        request = PostTranslationRequest(
            session_id="test",
            message_id=i,
            translation=sentence,
            is_final=False,
            original_language="en-dummy",
            language=language,
        )
        response = service(request)
        assert response.translation == expected[i]
        i += 1

    language, sentences = target_2

    for sentence in sentences:
        request = PostTranslationRequest(
            session_id="test",
            message_id=i,
            translation=sentence,
            is_final=False,
            original_language="en-dummy",
            language=language,
        )
        response = service(request)
        assert response.translation == expected[i]
        i += 1


@pytest.mark.parametrize(
    "language_1,sentences_1,language_2,sentences_2,expected",
    [
        (
            "en-US",
            ("The", "The quick", "The quick brown"),
            "zh",
            ("你", "你好", "你好我"),
            (
                "The",
                "The",
                "The quick brown",
                "你",
                "你",
                "你好我",
            ),
        ),
    ],
)
def test_translate_k_multi_language(
    language_1, sentences_1, language_2, sentences_2, expected
):
    """
    Test that post-translation with translate-k can handle a single
    session in multiple languages.
    """
    config = PostTranslationConfig(mask_k=0, translate_k=2)
    service = setup_service(config)
    i = 0

    for sentence in sentences_1:
        request = PostTranslationRequest(
            session_id="test",
            message_id=i,
            translation=sentence,
            is_final=False,
            original_language="en-dummy",
            language=language_1,
        )
        response = service(request)
        assert response.translation == expected[i]
        i += 1

    for sentence in sentences_2:
        request = PostTranslationRequest(
            session_id="test",
            message_id=i,
            translation=sentence,
            is_final=False,
            original_language="en-dummy",
            language=language_2,
        )
        response = service(request)
        assert response.translation == expected[i]
        i += 1


@pytest.mark.parametrize(
    "language,sentence,expected",
    [
        (
            "en-US",
            "this is fucking amazing",
            "this is f****** amazing",
        ),
        ("en-US", "I fucked up", "I f***** up"),
        ("en-US", "Shit! My bad!", "S***! My bad!"),
        ("zh", "他妈的是个傻逼。", "***是个**。"),
    ],
)
def test_remove_profanity(language, sentence, expected):
    """Test that remove profanity pass works correctly"""
    config = PostTranslationConfig(mask_k=0, translate_k=0, remove_profanity=True)
    service = setup_service(config)

    request = PostTranslationRequest(
        session_id="test",
        message_id=0,
        translation=sentence,
        is_final=False,
        original_language="en-US",
        language=language,
    )
    response = service(request)
    assert response.translation == expected


@pytest.mark.parametrize(
    "translation,is_final,expected",
    [
        ("kevin knight", True, "Kevin Knight."),
        ("kevin knight", False, "kevin knight"),
    ],
)
def test_punctuation_and_capitalization(translation, is_final, expected):
    """
    Test that post translation with punctuation and capitalization works as
    expected
    """
    config = PostTranslationConfig()
    config.mask_k = 0
    service = setup_service(config)

    request = PostTranslationRequest(
        session_id="test",
        message_id=0,
        translation=translation,
        is_final=is_final,
        original_language="en-US",
        language="en-US",
    )
    response = service(request)
    assert response.translation == expected
