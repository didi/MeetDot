import pytest
from unittest import mock

import utils

# Mock wav file duration time
utils.get_duration_seconds = mock.Mock(return_value=1)

from services.evaluation.asr.score import (
    get_finalization_time,
    score,
    score_latency,
)  # noqa: E402

wer_test_data = [
    # Simple test
    (["a", "b", "c"], ["a", "b", "c"], "en-US", 0.0),
    # Uneven number - measure first 2
    (["a", "c"], ["a", "b", "c"], "en-US", 50.0),
    # Test full word WER (1/4 words incorrect)
    (["abc def ghi", "b"], ["abc fed ghi", "b"], "en-US", 25.0),
    # Test case insensitive WER
    (["ABC DEF GHI", "B"], ["abc fed ghi", "b"], "en-US", 25.0),
    # Test chinese uses CER (2/10 characters incorrect)
    (["abc def ghi", "b"], ["abc fed ghi", "b"], "zh", 20.0),
]


@pytest.mark.parametrize("references,predictions,language,expected", wer_test_data)
def test_score_wer(references, predictions, language, expected):
    reference_languages = [language for _ in references]
    wer, _ = score(references, predictions, reference_languages)
    assert wer == expected


# Test latency computation
latency_test_data = [
    # Simple test - no flicker
    (
        ["a b c d"],
        [[(1.25, "a"), (1.5, "a b"), (1.75, "a b c"), (2.0, "a b c d")]],
        "en-US",
        1.0,
    ),
    # Test with flicker (latency increases)
    (
        ["a b c d"],
        [[(1.25, "a"), (1.5, "a b"), (1.75, "a c c"), (2.0, "a b c d")]],
        "en-US",
        4.75 / 4,  # ((1.25 - 0.25) + (2.0 - 0.5) + (2.0 - 0.75) + (2.0 - 1.0)) / 4
    ),
]


@pytest.mark.parametrize(
    "references,partial_transcripts,language,expected", latency_test_data
)
def test_score_latency(references, partial_transcripts, language, expected):
    latency = score_latency(
        references, [(None, language, None)] * len(references), partial_transcripts
    )
    assert latency == expected


# Test get_finalization_time (latency helper function)
finalization_test_data = [
    (
        ["a", "b", "c", "d"],
        2,
        [
            (1.0, ["a"]),
            (2.0, ["a", "b"]),
            (3.0, ["a", "b", "c"]),
            (4.0, ["a", "b", "c", "d"]),
        ],
        3.0,
    ),
    (
        ["a", "b", "c", "d"],
        0,
        [
            (1.0, ["a"]),
            (2.0, ["a", "b"]),
            (3.0, ["a", "b", "c"]),
            (4.0, ["a", "b", "c", "d"]),
        ],
        1.0,
    ),
    # Test flicker
    (
        ["a", "b", "c", "d"],
        1,
        [
            (1.0, ["a"]),
            (2.0, ["a", "b"]),
            (3.0, ["c", "b", "c"]),
            (4.0, ["a", "b", "c", "d"]),
        ],
        4.0,
    ),
    (
        ["a", "b", "c", "d"],
        0,
        [
            (1.0, ["a"]),
            (2.0, ["b", "b"]),
            (3.0, ["a", "b", "c"]),
            (4.0, ["a", "b", "c", "d"]),
        ],
        3.0,
    ),
]


@pytest.mark.parametrize(
    "final_transcript,j,partial_transcripts,expected", finalization_test_data
)
def test_finalization_time(final_transcript, j, partial_transcripts, expected):
    finalization_time = get_finalization_time(final_transcript, j, partial_transcripts)
    assert finalization_time == expected
