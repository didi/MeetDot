from collections import Counter


def prepare_history(lang: str, translations: dict, reactions: dict) -> str:
    """
    Return a conversation history from the perspective of a `lang` speaker

    Captions are shown in bilingual pairs, in `lang` and the original speaker language
    This is by design so if there's confusion, the reader can ask someone who understands
    the speaker's language, and is more likely to understand.
    """

    result = []

    # Store the utterances in all languages in a dictionary
    # so we can access by message_id in the original language
    by_message_id = {
        language: {msg["message_id"]: msg for msg in translations[language]}
        for language in translations
    }

    for u in translations[lang]:
        # TODO: Rate-limiting in the translator causes some messages in the catchup translator
        # to be dropped. This can cause some messages to not exist.
        original_utterance = by_message_id[u["speaker_language"]].get(
            u["message_id"], {"text": ""}
        )

        result.append(f"{u['speaker_name']} ({lang}): {u['text']}")
        if u["speaker_language"] != lang:
            result.append(f"({u['speaker_language']}): {original_utterance['text']}")
        if u["message_id"] in reactions:
            result.append(
                ", ".join(
                    f"{reaction}: {count}"
                    for reaction, count in Counter(
                        reactions[u["message_id"]].values()
                    ).most_common()
                )
            )
        result.append("")

    return "\n".join(result)
