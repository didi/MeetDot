import textwrap

import cjkwrap

from ..tokenizer import get_tokenizer
from .caption_strategy import CaptionStrategy
from .interface import CaptioningResponse


class WordLevelSlidingStrategy(CaptionStrategy):
    """
    given a text string and given caption config,
    do steps:
        1) Break text T into words
        2) Add words incrementally, from the end, stopping if:
                folding the collected words into lines yields > k lines
                (k == self.config["caption_lines"])
        3) Print those k lines
    return a text string after pruning, '\n' in the string representing line breaker.
    """

    def __call__(self, request):
        tokenizer = get_tokenizer(request.language)
        text = self.combine_speaker_utterances(
            request.session_id,
            request.language,
            request.utterance,
            request.utterance_complete,
        )
        tokens = tokenizer.tokenize(text)
        sliding_substr = ""
        sliding_window_tokens = []
        delay_time = 0.0
        target_language = request.language
        text_wrapper = cjkwrap if target_language == "zh" else textwrap

        for token in reversed(tokens):
            tmp_sliding_substr = tokenizer.detokenize(
                [token] + sliding_window_tokens[::-1]
            )
            lines_after_textwrap = text_wrapper.wrap(
                tmp_sliding_substr, self.config.characters_per_line
            )

            if len(lines_after_textwrap) <= self.config.num_lines:
                sliding_substr = tmp_sliding_substr
                sliding_window_tokens.append(token)
            else:
                # lines_after_textwrap over max caption lines

                break
        sliding_substr = tokenizer.detokenize(sliding_window_tokens[::-1])
        lines = text_wrapper.wrap(sliding_substr, self.config.characters_per_line)

        return CaptioningResponse(lines=lines, line_index=0), delay_time
