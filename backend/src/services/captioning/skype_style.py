import re
import textwrap
import time

import cjkwrap

from .caption_strategy import CaptionStrategy
from .interface import CaptioningResponse

min_read_time_per_line = 2  # 2 seconds per line


class SkypeStyleStrategy(CaptionStrategy):
    """
    given a text string and given caption config,
    do steps:
        1)
        2)
    return a text string after pruning, '\n' in the string representing line breaker.
    """

    def __call__(self, request):
        session_id = request.session_id
        target_language = request.language
        text_wrapper = cjkwrap if target_language == "zh" else textwrap

        self.requests_history_dict.setdefault((session_id, target_language), [])
        lines = []

        # check if remain_text overflow max_lines of caption window
        lines = text_wrapper.wrap(request.utterance, self.config.characters_per_line)

        if len(lines) > self.config.num_lines:
            lines = lines[: self.config.num_lines]

        # only emit caption current utterance is complete
        delay_time = 0.0

        if request.utterance_complete:
            ret_lines = lines
            delay_time = self.maintain_min_display_time(session_id, target_language)
            self.requests_history_dict[(session_id, target_language)].append(
                (time.time(), len(ret_lines))
            )
        else:
            ret_lines = []

        return (
            CaptioningResponse(lines=ret_lines, line_index=0),
            delay_time,
        )

    def maintain_min_display_time(self, session_id, target_language):
        # When displaying a string, estimate minimum time S for it to remain.

        if len(self.requests_history_dict[(session_id, target_language)]) > 0:
            cur_time = time.time()
            last_caption_start_time = self.requests_history_dict[
                (session_id, target_language)
            ][-1][0]
            last_caption_lines = self.requests_history_dict[
                (session_id, target_language)
            ][-1][1]
            min_wait_time = min_read_time_per_line * last_caption_lines
            actual_pass_time = cur_time - last_caption_start_time

            if actual_pass_time < min_wait_time:
                return min_wait_time - actual_pass_time

        return 0.0
