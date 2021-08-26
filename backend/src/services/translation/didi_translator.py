"""
DiDi fanyi translation service class (RESTful request)
"""
import json
import os
from enum import Enum

import requests

from .interface import TranslationRequest
from .translator import Translator


class DecodingMode(Enum):
    UNCONSTRAINED = 1
    HARD_PREFIX = 2
    BIASED = 3


class DiDiTranslator(Translator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.translate_url = os.getenv("DIDI_TRANSLATE_URL")
        base_url, _slash, _unused_part = self.translate_url.rpartition("/")
        self.lang_detect_url = f"{base_url}/lang_detect"

        self.apikey = os.getenv("DIDI_TRANSLATE_KEY")
        self.headers = {"Content-Type": "application/json", "apikey": self.apikey}

        if self.config.bias_beta <= 0:
            self.decoding_mode = DecodingMode.UNCONSTRAINED
            self.prefix_bias_beta = -1.0
        elif self.config.bias_beta >= 1:
            self.decoding_mode = DecodingMode.HARD_PREFIX
            self.prefix_bias_beta = 1.0
        else:
            self.decoding_mode = DecodingMode.BIASED
            self.prefix_bias_beta = self.config.bias_beta

        if self.config.custom_args and self.config.custom_args.get("disable_cache"):
            self.disable_cache = True
        else:
            self.disable_cache = False

        if self.config.custom_args:
            self.cache_key_prefix = self.config.custom_args.get("cache_key_prefix")
        else:
            self.cache_key_prefix = None

        if self.config.custom_args and self.config.custom_args.get("strongly_bias"):
            # For more info on "strongly_bias", see
            # https://docs.google.com/document/d/1o2ftbt16pkVmCjWNdl2rzEqVTjh0eWoegSHY0t57vMQ
            self.strongly_bias = True
        else:
            self.strongly_bias = False

    def post(self, url, request_dict):
        encoded_request = json.dumps(request_dict).encode("utf-8")
        response = requests.post(url, headers=self.headers, data=encoded_request).json()

        ret_code = response["code"]
        if ret_code != 0:
            self.logger.warning(f"Return code from {url} is not 0 ({ret_code})\n")
            self.logger.debug(response)
            return None
        else:
            return response

    def translate(self, request: TranslationRequest):
        """
        Call DiDi translator to get translation of request
        """

        if request.source_language == request.target_language:
            return request.text, None

        language_codes_map = {"zh": "zh", "en-US": "en", "es-ES": "es", "pt-BR": "pt"}
        data = {
            "text": request.text,
            "source": language_codes_map[request.source_language],
            "target": language_codes_map[request.target_language],
        }

        if self.disable_cache:
            data["cache_disabled"] = 1
        if self.cache_key_prefix:
            data["cache_key_prefix"] = str(self.cache_key_prefix)

        if (
            request.previous_translation
            and self.decoding_mode != DecodingMode.UNCONSTRAINED
        ):
            if request.source_language.lower().startswith(
                "en"
            ) and request.target_language.lower().startswith("zh"):
                for i in range(len(request.previous_translation)):

                    if (
                        not request.previous_translation[i]
                        or type(request.previous_translation[i]) == str
                    ):
                        continue

                    prefix_hash, raw_prefix = request.previous_translation[i]
                    if raw_prefix:
                        text = "".join(raw_prefix[-3:])
                        text = text.replace("@@", "")
                        lang_response = self.post(self.lang_detect_url, {"text": text})
                        lang = (
                            lang_response.get("data", {}).get("lang")
                            if lang_response
                            else None
                        )
                        if not lang or not lang.lower()[:2] in ("ja", "zh"):
                            request.previous_translation[i] = ["", []]
            data["prefix_bias_beta"] = self.prefix_bias_beta
            data["target_prefix"] = request.previous_translation

        translate_response = self.post(self.translate_url, data)
        translate_response = (
            {} if not translate_response else translate_response.get("data", {})
        )

        translation_text = translate_response.get("translation", "")
        raw_translation = translate_response.get("src_hashes_and_raw_tgt_splits")

        if raw_translation:
            if self.strongly_bias:
                for i in range(len(raw_translation)):
                    # clear all hashes, bias all future splits
                    raw_translation[i][0] = ""
            else:
                # Weak bias [default]:
                # We only clear the hash_suffix for the last split, since we expect the
                # input text for the last split to change on the next ASR pass.
                raw_translation[-1][0] = ""
        # TODO(scotfang): we could make biased-decoding more efficient by
        # only re-translating the latest split of each request, but that would
        # require us to keep track of the character indices for each split.
        # It's hard to keep track of the character indices because we have to map
        # from pre-processed/split text that has modified the original character
        # count back to the original un-preprocessed string.
        return translation_text, raw_translation if raw_translation else None
