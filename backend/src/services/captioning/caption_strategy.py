from typing import Tuple

from .interface import CaptioningConfig, CaptioningRequest, CaptioningResponse
from .utils import combine_utterances


class CaptionStrategy:
    """
    manage the caption strategy presenting to front-end,
    including things like how many lines for caption, how many characters per line,
    how the words update in the caption, etc.


    Captioning API input:
    {
        "language": text language code,
        “session_id”: unique session ID,
        “text”: translation text,
        “utterance_complete”: False
    }

    Captioning API output:
    {
        “session_id”: unique session ID,
        “lines”: captioning lines,
    }

    """

    def __init__(self, config: CaptioningConfig):
        self.config = config
        # session_id, target_language as unique keys
        self.requests_history_dict = {}
        self.completed_utterances = {}

    def __call__(self, request: CaptioningRequest) -> Tuple[CaptioningResponse, float]:
        """
        given a text string and given caption config,
        return a text string after pruning.
        Args:
            request:
        Returns:
            CaptioningResponse:
        """
        raise NotImplementedError

    def combine_speaker_utterances(
        self, session_id, target_language, last_utterance, last_utterance_complete=False
    ):
        """
        Helper function to combine all translated utterances from a speaker into one
        long string of multiple sentences.
        """
        key = (session_id, target_language)
        prev_utterances = self.completed_utterances.get(key, [])
        full_text = combine_utterances(
            target_language, prev_utterances, last_utterance, last_utterance_complete
        )

        if last_utterance_complete:
            self.completed_utterances.setdefault(key, [])
            self.completed_utterances[key].append(last_utterance)

        return full_text.strip()
