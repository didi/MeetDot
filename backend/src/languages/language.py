from pathlib import Path


class Language:
    """
    This class stores localized data and properties of different languages.
    """

    def __init__(self, language_tag: str, has_spaces: bool):
        """
        language_tag: the full BCP47 code used for ASR, including country code for most, e.g. en-US
        has_spaces: whether the language uses spaces as a word separator
        """

        # `language_tag`: the BCP47 code used by ASR, including country code for most, e.g. en-US
        self.language_tag = language_tag

        # `language_code`: the two or three character ISO language code (excludes country code)
        if "-" in language_tag:
            self.language_code, _, self.country_code = language_tag.partition("-")
        else:
            # this is not necessarily the country code, but for all the languages
            # Google ASR supports, it is
            self.country_code = self.language_code = language_tag

        # `has_spaces`: whether the language uses spaces between words
        # if it has spaces, we can match along word boundaries, otherwise
        # we have to just match substrings
        self.has_spaces = has_spaces

        # Load a list of words we don't want to show in transcripts
        with open(Path(__file__).parent / f"profanity.{language_tag}.txt") as fh:
            self.profane_words = [line.strip() for line in fh if line.strip()]
