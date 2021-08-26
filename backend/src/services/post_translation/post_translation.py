"""
The main responsibilites of PostTranslation class are:
1) initialize given strategy
2) take API request
3) remove profanity
4) return translation text after these processes


Post-translation API input:
{
    "session_id": unique session ID,
    "strategies": list of strategies want to be applied (e.g. ["translate-k", "mask-k"])
    "params": None or list of parameter sets for applied strategies, (e.g. [ {"k": 4}, {"k":5}])
    "translation": translation text,
    "is_final":  True/False (True if current translation text will not change
                             anymore, else False if the utterance is final, no
                             strategies will be applied)
}

Post-translation API output:
{
    "session_id": unique session ID,
    "translation": translation text after applying all enabled passes,
    "translation_update_status": True if current translation response is different
                                 with last timestamp response, else False
}

"""

import re
import os

from languages import languages
from ..tokenizer import get_tokenizer

from .interface import PostTranslationRequest, PostTranslationResponse
from utils import ThreadSafeDict

import requests


class PostTranslationService:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.do_translate_k = self.config.translate_k and self.config.translate_k > 0
        self.do_mask_k = self.config.mask_k and self.config.mask_k > 0
        # TODO(scotfang) make translate_k dictionaries garbage collect like an LRU cache
        self.translate_k_count = ThreadSafeDict()  # (session_id, language) as keys

        # We only do atomic reads/writes to this dict, so no need to make it a ThreadSafeDict.
        # TODO(scotfang) make translate_k dictionaries garbage collect like an LRU cache
        self.translate_k_cached_translations = {}

        # use punctuation server if it is specified in the env
        self.punctuation_server_url = os.getenv("PUNCTUATION_SERVER_URL")
        self.punctuation_server_enabled = (
            bool(self.punctuation_server_url) and self.config.add_punctuation
        )

        if self.punctuation_server_enabled:
            self.punctuation_server_active = self.test_punctuation_server()

    def test_punctuation_server(self):
        try:
            requests.post(
                f"{self.punctuation_server_url}/punctuate_and_capitalize",
                json={"text": "test", "language": "en-US"},
                timeout=1,
            )
            return True
        except requests.exceptions.ConnectionError:
            print(
                f"Could not connect to Punctuation server at "
                f"{self.punctuation_server_url} - is it running?"
            )
            return False

    def __call__(self, request: PostTranslationRequest) -> PostTranslationResponse:
        translation = self.post_translation(
            request.session_id,
            request.translation,
            request.original_language,
            request.language,
            request.is_final,
        )

        return PostTranslationResponse(
            translation=translation,
        )

    def post_translation(
        self, session_id, translation, original_language, language, asr_is_final
    ):
        """
        Note: all strategies only apply on current input utterance. PostTranslation service won't
        apply across previous utterances.
        Args:
            translation:
            asr_is_final: boolean, True if ASR service decides the current ASR text is finalized
                          and won't be changed anymore
        Return:
            translation: translated string after all passes
            mt_update_flag: True (in default) if the mt translation after anti-flicker methods
                            changes compared to previous time step translation
        """

        update = True
        key = f"{session_id}-{language}"

        if original_language != language and self.do_translate_k:
            update = self._update_translate_k(key, asr_is_final)
            if not update:
                translation = self.translate_k_cached_translations[key]

        if update:
            if original_language != language and self.do_mask_k:
                translation = self._mask_k(translation, language, asr_is_final)
            if self.config.remove_profanity:
                translation = self._remove_profanity(translation, language)

        if original_language != language and self.do_translate_k:
            if asr_is_final:
                # TODO(scotfang): If a stale final request gets skipped in translator.py,
                #                 we won't clear these cached translations like we're supposed to.
                self.translate_k_cached_translations[key] = ""
            elif update:
                self.translate_k_cached_translations[key] = translation

        self.logger.debug(
            f"session id: {session_id}, translation str after post-translation: {translation}"
        )

        # call punctuation and capitalization server to insert punctuations
        # and revise capitalization
        if (
            asr_is_final
            and self.punctuation_server_enabled
            and self.punctuation_server_active
        ):
            resp = requests.post(
                f"{self.punctuation_server_url}/punctuate_and_capitalize",
                json={"text": translation, "language": language},
            )
            translation = resp.json()["text"]

        return translation

    def _update_translate_k(self, key, asr_is_final):
        """
        Return:
            update_flag: bool, indicating if the translation should be updated.
        """

        with self.translate_k_count as counts:
            if key not in counts:
                counts[key] = 0
            ct = counts[key]
            counts[key] += 1

        if asr_is_final or ct % self.config.translate_k == 0:
            return True
        else:
            return False

    def _mask_k(self, translation, language, asr_is_final):
        """
        implement the mask k strategy mentioned in google's paper
        https://arxiv.org/pdf/1912.03393.pdf
        definition: mask the last k tokens of the predicted target sentence;
        - The masking is only applied if the current source are prefixes and not yet
          completed sentences.
        Args:

        Return:
            translation string
        """

        if not asr_is_final:
            # if asr text is not finalized, mask the last k tokens of the predicted target
            tokenizer = get_tokenizer(language)
            translation_tokens = tokenizer.tokenize(translation)
            translation_tokens_masked = translation_tokens[: -self.config.mask_k]
            if not translation_tokens_masked and self.config.disable_masking_before_k:
                translation_tokens_masked = translation_tokens
            translation = tokenizer.detokenize(translation_tokens_masked)

        return translation

    def _remove_profanity(self, translation, language):
        """
        Remove profane words using a simple per-language word list.
        This is not perfect, but probably good enough, since all words
        must have come through the ASR anyways.
        """

        lang = languages[language]

        for word in lang.profane_words:
            if lang.has_spaces:
                translation = re.sub(
                    fr"\b{word}\b",
                    lambda word: word[0][0] + "*" * (len(word[0]) - 1),
                    translation,
                    flags=re.IGNORECASE,
                )
            else:
                translation = translation.replace(word, "*" * len(word))
        return translation
