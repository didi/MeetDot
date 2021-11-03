from unittest import mock

import pytest
from services.post_asr import (
    PostASRConfig,
    PostASRRequest,
    PostASRService,
)


def setup_service(config):
    logger = mock.Mock()

    return PostASRService(config, logger)


@pytest.mark.parametrize(
    "asr_output,expected",
    [
        ("Tennis tennis!", "Tennis"),
        ("Wait, wait wait, wait.", "Wait, wait wait, wait."),
        ("Hello!", "Hello!"),
        (
            "The quick brown fox fox fox FOX fOX jumped over",
            "The quick brown fox jumped over",
        ),
        ("what What, is this?", "What, is this?"),
        ("What is this this, this?", "What is this?"),
    ],
)
def test_post_asr_repetition_removal(asr_output, expected):
    """
    Test that post asr with repetition removal works as expected
    """
    config = PostASRConfig(remove_repetitions=True)
    service = setup_service(config)

    request = PostASRRequest(
        transcript=asr_output,
        language="en-US",
    )

    response = service(request)
    assert response.transcript == expected
