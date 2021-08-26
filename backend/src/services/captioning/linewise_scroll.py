from collections import defaultdict
from typing import List, Tuple

import cjkwrap

from .caption_strategy import CaptionStrategy
from .interface import CaptioningConfig, CaptioningRequest, CaptioningResponse
from .pswrap import pswrap


class LinewiseScrollStrategy(CaptionStrategy):
    """
    given a text string and given caption config,
    do steps:
        1) Folding text T into lines
        2) print last k lines, (k == self.config.caption_lines)
    return a text string after pruning, '\n' in the string representing line breaker.
    """

    def __init__(self, config: CaptioningConfig):
        super().__init__(config)
        self.prev_lines = defaultdict(list)
        self.prev_line_index = defaultdict(int)

    def __call__(self, request: CaptioningRequest) -> Tuple[CaptioningResponse, float]:
        delay_time = 0.0
        session_id = request.session_id
        target_language = request.language
        if self.config.punctuation_sensitive:
            text_wrapper = pswrap
        else:
            text_wrapper = cjkwrap.wrap

        text = self.combine_speaker_utterances(
            request.session_id,
            request.language,
            request.utterance,
            request.utterance_complete,
        )

        lines = text_wrapper(text, self.config.characters_per_line)
        line_index = max(0, len(lines) - self.config.num_lines)
        lines = lines[-self.config.num_lines :]

        if not request.utterance_complete:
            # highlight is only enabled when utterance is incomplete
            highlight_boundaries = LinewiseScrollStrategy.get_highlight(
                self.prev_lines[(session_id, target_language)][
                    line_index - self.prev_line_index[(session_id, target_language)] :
                ],
                lines,
                line_index,
            )
        else:
            highlight_boundaries = [-1] * len(lines)

        self.prev_lines[(session_id, target_language)] = lines
        self.prev_line_index[(session_id, target_language)] = line_index

        return (
            CaptioningResponse(
                lines=lines,
                line_index=line_index,
                highlight_boundaries=highlight_boundaries,
            ),
            delay_time,
        )

    @staticmethod
    def get_highlight(
        prev_lines: List[str], lines: List[str], line_index: int
    ) -> List[int]:
        """
        Given text, text from the previous timestamp and caption lines,
        return which parts of the line differ from the previous.

        For example,
        if input `lines` is ["January February", "March April", "May"] and the previous text
        is ["January February", "March"]
        this will return: [-1, 6, 0], corresponding to highlighting: " April" in the second line
        and "May" in the third.
        """
        result = []

        for prev_line, line in zip(prev_lines, lines):
            if prev_line == line:
                # Highlight nothing on this line
                result.append(-1)
            else:
                # Highlight starting from the difference
                prefix_length = LinewiseScrollStrategy.get_common_prefix(
                    prev_line, line
                )
                result.append(prefix_length)

                break

        # Highlight all subsequent lines
        result.extend([0] * (len(lines) - len(result)))

        return result

    @staticmethod
    def get_common_prefix(s1: str, s2: str) -> int:
        """Get the length of the common prefix of s1, s2"""

        for i, (c1, c2) in enumerate(zip(s1, s2)):
            if c1 != c2:
                return i

        return min(len(s1), len(s2))
