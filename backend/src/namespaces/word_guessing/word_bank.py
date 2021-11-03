import random
from csv import reader
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Word:
    translations: Dict[str, List[str]] = field(default_factory=lambda: {})

    def add_translation(self, language: str, translation: List[str]):
        self.translations[language] = translation

    def has_translations(self, languages):
        return all(language in self.translations for language in languages)

    def __hash__(self):
        return id(self.translations)


class WordBank:
    words = None

    def __init__(self, words):
        self.words = words
        self.index = random.randrange(max(1, len(words)))

    def get_next(self):
        word = self.words[self.index] if len(self.words) else Word()
        self.index = (self.index + 1) % len(self.words)

        return word

    @staticmethod
    def get_word_bank(languages, words_file="resources/words.tsv", shuffle=True):
        if WordBank.words is None:
            # Load words from file
            words = {}
            with open(words_file) as f:
                word_reader = reader(f, delimiter="\t")

                for word_set in word_reader:
                    word = None

                    for translation in word_set:
                        if translation in words:
                            word = words[translation]

                            break

                    if word is None:
                        word = Word()

                    for translation in word_set:
                        words[translation] = word
                        language, text = translation.split("=")
                        word.add_translation(language, text.split(","))

            words = list(set(words.values()))

            if shuffle:
                random.shuffle(words)
            WordBank.words = words

        filtered_words = list(
            filter(lambda w: w.has_translations(languages), WordBank.words)
        )

        return WordBank(filtered_words)
