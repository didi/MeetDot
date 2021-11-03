import re
import string

import requests

from .interface import PostASRRequest, PostASRResponse


class PostASRService:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

    def __call__(self, request: PostASRRequest) -> PostASRResponse:
        transcript = self.post_asr(
            request.transcript,
            request.language,
        )

        return PostASRResponse(
            transcript=transcript,
        )

    def _get_simplified_word(self, word):
        return word.upper().translate(str.maketrans("", "", string.punctuation))

    def post_asr(self, transcript, language):
        if self.config.remove_repetitions and len(transcript) > 0:
            if language == "en-US":
                # just for fun
                # out=re.sub(r'(?!\b(?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|wait)\
                # \b)\b(\w+)(?:[,.! ]+\1\b)+', r'\1', transcript, flags=re.IGNORECASE)
                skip_set = {
                    "ONE",
                    "TWO",
                    "THREE",
                    "FOUR",
                    "FIVE",
                    "SIX",
                    "SEVEN",
                    "EIGHT",
                    "NINE",
                    "TEN",
                    "TWENTY",
                    "WAIT",
                }
                out = []
                words = transcript.split()
                prev_w_simplified = None
                for w in words:
                    w_simplified = self._get_simplified_word(w)
                    if w_simplified in skip_set:
                        out.append(w)
                        prev_w_simplified = w_simplified
                    elif len(out) == 0 or prev_w_simplified != w_simplified:
                        out.append(w)
                        prev_w_simplified = w_simplified
                    elif w[-1] in string.punctuation and not out[-1][0].isupper():
                        out[-1] = w
                        prev_w_simplified = w_simplified
                return " ".join(out)

        return transcript
