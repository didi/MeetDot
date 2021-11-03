import html
import logging
import time

import jieba
from sacremoses import MosesDetokenizer, MosesTokenizer

TOKENIZERS = {}
SUPPORTED_LANGUAGES = ("en-US", "zh", "es-ES", "pt-BR")


def get_tokenizer(language):
    # Load tokenizers only once per language

    if language not in TOKENIZERS:
        TOKENIZERS[language] = Tokenizer(language)

    return TOKENIZERS[language]


class Tokenizer:
    def __init__(self, lang="en-US", logger_name=None):
        self.logger = (
            logging.getLogger(logger_name)
            if logger_name
            else logging.getLogger(__name__)
        )

        self.lang = lang

        if self.lang not in SUPPORTED_LANGUAGES:
            self.logger.error(f"Unsupported language for tokenizer: {self.lang}")
            raise ValueError(f"Unsupported languages for tokenizer: {self.lang}")

        if self.lang == "en-US":
            s_time = time.time()
            self.tokenizer = MosesTokenizer(lang="en")
            self.detokenizer = MosesDetokenizer(lang="en")
            e_time = time.time()
            self.logger.info(f"Time to load English Tokenizer: {e_time - s_time}")

        if self.lang == "zh":
            s_time = time.time()
            jieba.setLogLevel(logging.ERROR)
            jieba.initialize()
            e_time = time.time()
            self.logger.info(f"Time to initialize jieba: {e_time - s_time}")

        if self.lang == "es-ES":
            s_time = time.time()
            try:
                self.tokenizer = MosesTokenizer(lang="es")
                self.detokenizer = MosesDetokenizer(lang="es")
            except Exception as exception:
                self.logger.error(exception, exc_info=True)
            e_time = time.time()
            self.logger.info(f"Time to load Spanish Tokenizer: {e_time - s_time}")

        if self.lang == "pt-BR":
            s_time = time.time()
            try:
                self.tokenizer = MosesTokenizer(lang="pt")
                self.detokenizer = MosesDetokenizer(lang="pt")
            except Exception as exception:
                self.logger.error(exception, exc_info=True)
            e_time = time.time()
            self.logger.info(f"Time to load Portuguese Tokenizer: {e_time - s_time}")

    def tokenize(self, input_str):
        """
        Args:
            input_str: input string
        Returns:
            tokens: list of tokens
        """
        ret_tokens = []

        if self.lang == "zh":
            seg_tokens = jieba.cut(input_str)  # 默认是精确模式
            ret_tokens = list(seg_tokens)

            return ret_tokens
        else:
            ret_tokens = self.tokenizer.tokenize(input_str)
            ret_tokens = list(map(html.unescape, ret_tokens))

            return ret_tokens

    def detokenize(self, tokens):
        """
        Args:
            tokens: list of token in str format
        """

        if self.lang == "zh":
            return "".join(tokens)
        else:
            return self.detokenizer.detokenize(tokens)
