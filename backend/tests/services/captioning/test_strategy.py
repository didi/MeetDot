import pytest
from services.captioning import CaptioningConfig
from services.captioning.caption_strategy import CaptionStrategy

test_data = [
    # Empty test
    (("en-US",), ("",), (False,), ("",)),
    # Simple test with a single utterance
    (
        ("en-US", "en-US"),
        ("Hello", "Hello world"),
        (False, True),
        ("Hello", "Hello world."),
    ),
    # Test no double punctuation
    (
        ("en-US", "en-US", "en-US"),
        ("Hello", "Hello world", "Hello world!"),
        (False, False, True),
        ("Hello", "Hello world", "Hello world!"),
    ),
    # Test multiple utterances
    (
        ("en-US", "en-US", "en-US"),
        ("Hello", "Hello world", "Hello"),
        (False, True, True),
        ("Hello", "Hello world.", "Hello world. Hello."),
    ),
]


@pytest.mark.parametrize(
    "languages,utterances,utterance_completes,expecteds", test_data
)
def test_combine_utterances(languages, utterances, utterance_completes, expecteds):
    config = CaptioningConfig()
    strategy = CaptionStrategy(config)

    for i in range(len(utterances)):
        text = strategy.combine_speaker_utterances(
            key=("test", languages[i], languages[i]),
            last_utterance=utterances[i],
            last_utterance_complete=utterance_completes[i],
        )
        assert text == expecteds[i]
