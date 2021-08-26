UTTERANCE_DELIMITERS = {
    "es-ES": ".",
    "en-US": ".",
    "zh": "。",
}
DELIMITERS = "\"'.?!。？！,，"


def combine_utterances(
    target_language, prev_utterances, last_utterance, last_utterance_complete
):
    """
    Helper function to combine utterances into one
    long string of multiple sentences.
    """
    delimiter = UTTERANCE_DELIMITERS.get(target_language, ". ")
    full_text = ""
    utterances_splitter = " " if target_language != "zh" else ""
    # Note: this implementation assumes utterance_splitter will always be whitespace

    for utterance in prev_utterances:
        utterance = utterance.strip()
        full_text += utterance
        if full_text and full_text[-1] not in DELIMITERS:
            full_text += delimiter
        full_text += utterances_splitter

    full_text = (
        full_text.rstrip() + utterances_splitter + last_utterance.lstrip()
    ).strip()

    if last_utterance_complete:
        if len(full_text) and full_text[-1] not in DELIMITERS:
            full_text += delimiter
    return full_text


def get_word_separator(language):
    return " " if language != "zh" else ""
