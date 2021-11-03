import pytest
from services.captioning import CaptioningRequest, CaptioningResponse
from services.evaluation.st.evaluate import on_caption

test_data = [
    # One line output with flickering
    (
        ("Hello", "Hello!", "This is", "Is this a test", "Is this a test?"),
        (False, True, False, False, True),
        (
            ["Hello"],
            ["Hello!"],
            ["Hello! This is"],
            ["Hello! Is this a test"],
            ["Hello! Is this a test?"],
        ),
        (
            "Hello",
            "Hello!",
            "Hello! This is",
            "Hello! Is this a test",
            "Hello! Is this a test?",
        ),
    ),
    # Two line output with flickering
    (
        ("Hello", "Hello!", "This is", "Is this a test", "Is this a test?"),
        (False, True, False, False, True),
        (
            ["Hello", ""],
            ["Hello!", ""],
            ["Hello!", "This is"],
            ["Hello!", "Is this a test"],
            ["Hello!", "Is this a test?"],
        ),
        (
            "Hello",
            "Hello!",
            "Hello! This is",
            "Hello! Is this a test",
            "Hello! Is this a test?",
        ),
    ),
    # One line output with flickering and cut off
    (
        (
            "Hello",
            "Hello!",
            "This is",
            "Is this a",
            "Is this a test",
            "Is this a test?",
        ),
        (False, True, False, False, False, True),
        (
            ["Hello"],
            ["Hello!"],
            ["Hello! This is"],
            ["Is this a"],
            ["test"],
            ["test?"],
        ),
        (
            "Hello",
            "Hello!",
            "Hello! This is",
            "Hello! Is this a",
            "Hello! Is this a test",
            "Hello! Is this a test?",
        ),
    ),
    (
        (
            "Test sentence",
            "Test sentence A.",
            "Sentence",
            "Sentence B.",
            "I am testing",
            "Ham testing sentence",
            "I am testing sentence C.",
        ),
        (False, True, False, True, False, False, True),
        (
            ["", ""],
            ["Test sentence A.", ""],
            ["Test sentence A.", ""],
            ["Test sentence A.", "Sentence B."],
            ["Test sentence A.", "Sentence B."],
            ["Test sentence A.", "Sentence B."],
            ["Sentence B.", "I am testing sentence C."],
        ),
        (
            "",
            "Test sentence A.",
            "Test sentence A.",
            "Test sentence A. Sentence B.",
            "Test sentence A. Sentence B.",
            "Test sentence A. Sentence B.",
            "Test sentence A. Sentence B. I am testing sentence C.",
        ),
    ),
    (
        (
            "A B C D E",
            "A B C D F E G.",
            "T U V",
            "T U V X Y Z.",
        ),
        (False, True, False, True),
        (
            ["A B C", "D E"],
            ["B C D", "F E G."],
            ["F E G.", "T U V"],
            ["T U V", "X Y Z."],
        ),
        (
            "A B C D E",
            "A B C D F E G.",
            "A B C D F E G. T U V",
            "A B C D F E G. T U V X Y Z.",
        ),
    ),
]


@pytest.mark.parametrize(
    "utterances,utterance_completes,output_lines,expected_partial_captions", test_data
)
def test_on_caption(
    utterances, utterance_completes, output_lines, expected_partial_captions
):
    translations = {}
    prefixes = {}
    test_session_id = "test"
    i = 0

    for utterance, utterance_complete, lines, expected_partial_caption in zip(
        utterances, utterance_completes, output_lines, expected_partial_captions
    ):
        request = CaptioningRequest(
            session_id=test_session_id,
            message_id=0,
            original_language="en-US",
            target_language="en-US",
            utterance=utterance,
            utterance_complete=utterance_complete,
        )
        response = CaptioningResponse(lines=lines, line_index=0)
        on_caption(request, response, prefixes, translations)
        i += 1

    assert test_session_id in translations

    for i, (_, partial_translation) in enumerate(translations[test_session_id]):
        assert partial_translation == expected_partial_captions[i]
