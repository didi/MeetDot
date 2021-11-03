import pytest
from services.captioning import CaptioningConfig, CaptioningRequest
from services.captioning.linewise_scroll import LinewiseScrollStrategy

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
        ["jumped over the lazy", "dog."],
    ),
    # 1 line output, cut off
    (
        1,
        "The quick brown fox jumped",
        "en-US",
        20,
        ["jumped"],
    ),
    # Spanish long string
    (
        2,
        "Long Beach, fundada en 1897, es una ciudad del condado de Los Ángeles en el estado estadounidense de California. En 2009 tenía una población de 492.682 habitantes y una densidad poblacional de 3.772,45 personas por km². La ciudad es sede de un aeropuerto nacional y el mayor puerto marítimo industrial de la región de Los Ángeles. El circuito callejero de Long Beach es uno de los más reconocidos de su tipo a nivel mundial.",  # noqa: E501
        "es-ES",
        30,
        ["reconocidos de su tipo a nivel", "mundial."],
    ),
    # Chinese string
    (2, "一二三,四五六,七八九,十十一十二,十三十四十五,十六十七十,八十九二十.", "zh", 6, ["九二十", "."]),
]


@pytest.mark.parametrize("num_lines,s,language,chars_per_line,expected", test_data)
def test_linewise_scroll(num_lines, s, language, chars_per_line, expected):
    config = CaptioningConfig(
        strategy="linewise_scroll",
        num_lines=num_lines,
        characters_per_line=chars_per_line,
        punctuation_sensitive=False,
    )
    strategy = LinewiseScrollStrategy(config)
    request = CaptioningRequest(
        session_id="test",
        message_id=0,
        original_language=language,
        target_language=language,
        utterance=s,
        utterance_complete=False,
    )
    output, output_delay = strategy(request)
    assert output.lines == expected
    assert output_delay == 0.0


test_punctuation_sensitive_data = [
    # Test punctuation sensitive text wrapper
    (
        2,
        "The, quick, brown, fox, jumped, over, the lazy dog.",
        "en-US",
        20,
        ["jumped, over, the lazy", "dog."],
    ),
    (
        2,
        "The,,,,,,,,,,,, quick brown fox jumped over the lazy dog.",
        "en-US",
        20,
        ["jumped over the lazy", "dog."],
    ),
    (
        2,
        "The quick brown fox jumped over,,,,,,,,,,,, the lazy dog.",
        "en-US",
        20,
        ["jumped over,,,,,,,,,,,, the lazy", "dog."],
    ),
    # Chinese string
    (2, "一二，，，三四，五，，，六，", "zh", 6, ["一二，，，三", "四，五，，，六，"]),
    (2, "七八九，十十一十二，", "zh", 6, ["十十一", "十二，"]),
    (2, "一二三，四五六，七八九，十十一十二，十三十四十五，十六十七十，八十九二十。", "zh", 6, ["十，八十", "九二十。"]),
    (2, "一二三，四五六，七八九，十十一十二，十三十四十五，十六十七十，八十，，，，，，九二十", "zh", 6, ["十，八十，，，，，，", "九二十"]),
]


@pytest.mark.parametrize(
    "num_lines,s,language,chars_per_line,expected",
    test_punctuation_sensitive_data,
)
def test_linewise_scroll_punctuation_sensitive_wrapper(
    num_lines, s, language, chars_per_line, expected
):
    config = CaptioningConfig(
        strategy="linewise_scroll",
        num_lines=num_lines,
        characters_per_line=chars_per_line,
        punctuation_sensitive=True,
    )
    strategy = LinewiseScrollStrategy(config)
    request = CaptioningRequest(
        session_id="pswrapper test",
        message_id=0,
        original_language=language,
        target_language=language,
        utterance=s,
        utterance_complete=False,
    )
    output, output_delay = strategy(request)
    assert output.lines == expected
    assert output_delay == 0.0


test_highlight_data = [
    ([""], "", "en-US", [], []),
    (
        [""],
        "alpha bravo charlie delta echo foxtrot golf",
        "en-US",
        ["delta echo foxtrot", "golf"],
        [0, 0],
    ),
    (
        ["alpha bravo charlie", "delta echo"],
        "alpha bravo charlie delta echo foxtrot golf",
        "en-US",
        ["delta echo foxtrot", "golf"],
        [10, 0],
    ),
    (
        ["alpha bravo charlie", "delta echo foxtrot"],
        "alpha bravo charlie delta echo foxtrot golf",
        "en-US",
        ["delta echo foxtrot", "golf"],
        [-1, 0],
    ),
    (
        ["alpha bravo charlie", "delta echo foxtrot", "golf hotel india"],
        "alpha bravo charlie delta echo foxtrot golf",
        "en-US",
        ["delta echo foxtrot", "golf"],
        [-1, 4],
    ),
    (
        ["alpha bravo charlie", "delta echo foxtrot", "goal hotel india"],
        "alpha bravo charlie delta echo foxtrot golf",
        "en-US",
        ["delta echo foxtrot", "golf"],
        [-1, 2],
    ),
]


@pytest.mark.parametrize(
    "prev_lines, text, language, expected, expected_boundaries",
    test_highlight_data,
)
def test_highlight(
    prev_lines: list,
    text: str,
    language: str,
    expected: list,
    expected_boundaries: list,
):
    config = CaptioningConfig(
        strategy="linewise_scroll",
        num_lines=2,
        characters_per_line=20,
    )
    session_id = "session"
    strategy = LinewiseScrollStrategy(config)
    strategy.prev_lines[("session", language, language)] = prev_lines
    request = CaptioningRequest(
        session_id=session_id,
        message_id=0,
        original_language=language,
        target_language=language,
        utterance=text,
        utterance_complete=False,
    )
    output, output_delay = strategy(request)
    assert output.lines == expected
    assert output.highlight_boundaries == expected_boundaries


def test_multiple_speakers():
    strategy = LinewiseScrollStrategy(
        CaptioningConfig(
            strategy="linewise_scroll",
            num_lines=2,
            characters_per_line=20,
        )
    )
    strategy.prev_lines[("speaker1", "en-US", "en-US")] = ["Hello"]
    strategy.prev_lines[("speaker2", "es-ES", "es-ES")] = ["Hola"]

    request = CaptioningRequest(
        session_id="speaker1",
        message_id=0,
        original_language="en-US",
        target_language="en-US",
        utterance="Hello, my name is",
        utterance_complete=False,
    )
    output, output_delay = strategy(request)
    assert output.lines == ["Hello, my name is"]
    assert output.highlight_boundaries == [5]


test_common_prefix_data = [
    ("abcde", "abc", 3),
    ("abcde", "abcaaaaa", 3),
    ("", "abcaaaaaaa", 0),
    ("", "", 0),
    ("defghi", "defghi", 6),
]


@pytest.mark.parametrize("s1, s2, expected_result", test_common_prefix_data)
def test_common_prefix(s1, s2, expected_result):
    assert LinewiseScrollStrategy.get_common_prefix(s1, s2) == expected_result


def test_sequence_requests():
    """Simulating a sequence requests to test."""

    test_seq_data = [
        ("zh", "测试测试", False, [0]),
        ("zh", "测试测试。", True, [-1]),
        ("zh", "星期一", False, [5]),
        ("zh", "星期一星期二", False, [8]),
        ("zh", "星期一星期二星期三", False, [11, 0]),
        ("zh", "星期一星期二星期三。", True, [-1, -1]),
        ("zh", "星期四新奇。", False, [-1, 3]),
        ("zh", "星期四星期五。", True, [-1, -1]),
    ]

    config = CaptioningConfig(
        strategy="linewise_scroll",
        num_lines=2,
        characters_per_line=24,
        punctuation_sensitive=False,
    )
    strategy = LinewiseScrollStrategy(config)

    for item in test_seq_data:
        request = CaptioningRequest(
            session_id="test",
            message_id=0,
            original_language=item[0],
            target_language=item[0],
            utterance=item[1],
            utterance_complete=item[2],
        )
        output, output_delay = strategy(request)
        boundary = output.highlight_boundaries
        assert boundary == item[3]
