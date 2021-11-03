import string

from .zh import NSWNormalizer, CHINESE_PUNC_LIST

NORMALIZERS = {}
SUPPORTED_LANGUAGES = "zh"


def get_normalizer(language):
    # Load normalizer only once per language

    if language not in NORMALIZERS:
        NORMALIZERS[language] = Normalizer(language)

    return NORMALIZERS[language]


class Normalizer:
    def __init__(self, lang):
        self.lang = lang

        if self.lang not in SUPPORTED_LANGUAGES:
            self.logger.error(f"Unsupported language for tokenizer: {self.lang}")
            raise ValueError(f"Unsupported languages for tokenizer: {self.lang}")

        if lang == "zh":
            old_chars = CHINESE_PUNC_LIST + string.punctuation
            new_chars = " " * len(old_chars)
            del_chars = ""
            trans = str.maketrans(old_chars, new_chars, del_chars)

            def normalize(text):
                text = text.lower()
                text = NSWNormalizer(text).normalize()
                text = text.translate(trans)

                return text

        self.normalize = normalize

    def normalize(self, text):
        # Overridden in __init__ for each language
        raise NotImplementedError
