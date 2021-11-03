from languages import languages

DELIMITERS = "\"'.?!。？！,，"


def combine_utterances(
    target_language, prev_utterances, last_utterance, last_utterance_complete
):
    """
    Helper function to combine utterances into one
    long string of multiple sentences.
    """
    eos_punctuation = languages[target_language].eos_punctuation
    word_separator = languages[target_language].word_separator
    full_text = ""
    # Note: this implementation assumes utterance_splitter will always be whitespace

    for utterance in prev_utterances:
        utterance = utterance.strip()
        full_text += utterance
        if full_text and full_text[-1] not in DELIMITERS:
            full_text += eos_punctuation
        full_text += word_separator

    full_text = (full_text.rstrip() + word_separator + last_utterance.lstrip()).strip()

    if last_utterance_complete:
        if len(full_text) and full_text[-1] not in DELIMITERS:
            full_text += eos_punctuation
    return full_text


def get_word_separator(language):
    return " " if language != "zh" else ""
