import pytest
from services.captioning import CaptioningConfig, CaptioningRequest
from services.captioning.word_level_sliding import WordLevelSlidingStrategy

test_data = [
    # Empty test
    (
        2,
        "",
        "en-US",
        20,
        [],
    ),
    # Simple test, everything visible
    (
        2,
        "The quick brown",
        "en-US",
        20,
        ["The quick brown"],
    ),
    # Two lines
    (
        2,
        "The quick brown fox jumped over",
        "en-US",
        20,
        ["The quick brown fox", "jumped over"],
    ),
    # Test lines being cut off
    (
        2,
        "The quick brown fox jumped over the lazy dog.",
        "en-US",
        20,
        ["brown fox jumped", "over the lazy dog."],
    ),
    # 1 line output, cut off
    (1, "The quick brown fox jumped", "en-US", 20, ["brown fox jumped"]),
    # Spanish long string
    (
        2,
        "Long Beach, fundada en 1897, es una ciudad del condado de Los Ángeles en el estado estadounidense de California. En 2009 tenía una población de 492.682 habitantes y una densidad poblacional de 3.772,45 personas por km². La ciudad es sede de un aeropuerto nacional y el mayor puerto marítimo industrial de la región de Los Ángeles. El circuito callejero de Long Beach es uno de los más reconocidos de su tipo a nivel mundial.",  # noqa: E501
        "es-ES",
        30,
        ["es uno de los más reconocidos", "de su tipo a nivel mundial."],
    ),
]


@pytest.mark.parametrize("num_lines,s,language,chars_per_line,expected", test_data)
def test_linewise_scroll(num_lines, s, language, chars_per_line, expected):
    config = CaptioningConfig(
        strategy="wordwise_sliding_window",
        num_lines=num_lines,
        characters_per_line=chars_per_line,
    )
    strategy = WordLevelSlidingStrategy(config)
    request = CaptioningRequest(
        session_id="test",
        message_id=0,
        language=language,
        utterance=s,
        utterance_complete=False,
    )
    output, output_delay = strategy(request)
    assert output.lines == expected
    assert output_delay == 0.0
