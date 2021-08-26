import logging
import os
from dataclasses import dataclass

from services.captioning.utils import get_word_separator
from services.evaluation.asr.score import score as score_wer
from services.evaluation.asr.score import score_wer_by_speaker
from services.evaluation.asr.score import score_name_f1
from services.evaluation.score import EvaluationScore
from services.evaluation.translation.score import score as score_bleu
from services.tokenizer import get_tokenizer
from statistics import mean
from utils import get_duration_seconds


@dataclass
class SpeechTranslationEvaluationScore(EvaluationScore):
    wer: float
    wer_per_speaker: str
    bleu: float
    normalized_erasure: float
    translation_lag: float
    initial_asr_lag: float
    initial_caption_lag: float
    initial_asr_caption_lag: float
    incremental_caption_lag: float
    max_burstiness: float
    mean_burstiness: float
    name_precision: float
    name_recall: float
    name_f1: float


def score_word_burstiness(partial_translations, target_language):
    """Measures the max and mean change in the number of words from one caption
    to the next.  The max and mean are taken per utterance, and then averaged
    over the entire dataset.

    For Chinese, characters are used instead of words to measure burst size.
    """
    word_separator = get_word_separator(target_language)

    if not partial_translations:
        return 0
    max_word_burst_per_utterance = []
    mean_word_burst_per_utterance = []

    for utterance_translations in partial_translations:
        prev_translation_and_num_words = (None, 0)
        utterance_burst_sizes = []
        for _timestamp, translation in utterance_translations:
            if translation == prev_translation_and_num_words[0]:
                continue
            if word_separator:
                num_words = len(translation.split(word_separator)) if translation else 0
            else:
                num_words = len(translation) if translation else 0
            burst_size = abs(num_words - prev_translation_and_num_words[1])
            prev_translation_and_num_words = (translation, num_words)
            if burst_size:
                utterance_burst_sizes.append(burst_size)

        if utterance_burst_sizes:
            max_word_burst_per_utterance.append(max(utterance_burst_sizes))
            mean_word_burst_per_utterance.append(mean(utterance_burst_sizes))

    return (
        mean(max_word_burst_per_utterance) if max_word_burst_per_utterance else 0.0,
        mean(mean_word_burst_per_utterance) if mean_word_burst_per_utterance else 0.0,
    )


def score_initial_caption_lag(initial_caption_times):
    """Measures the time between when the wav file starts playback and when
    the first non-empty caption is seen"""
    initial_caption_times = list(filter(lambda x: x >= 0, initial_caption_times))

    if not initial_caption_times:
        return 0.0

    return sum(lag_in_seconds for lag_in_seconds in initial_caption_times) / float(
        len(initial_caption_times)
    )


def score_initial_asr_caption_lag(partial_transcripts, partial_translations):
    """Measures the time between the first non-empty asr transcription and
    the first non-empty caption."""
    assert len(partial_transcripts) == len(partial_translations)
    if not partial_transcripts:
        return 0.0

    all_asr_caption_lags = []
    for utterance_asr, utterance_translations in zip(
        partial_transcripts, partial_translations
    ):
        time_asr = None
        for t0, asr in utterance_asr:
            if asr.strip():
                time_asr = t0
                break
        if time_asr is None:
            continue

        time_translation = None
        for t1, translation in utterance_translations:
            if translation.strip():
                time_translation = t1
                break
        if time_translation is None:
            time_translation = utterance_translations[-1][0]

        assert time_translation >= time_asr
        all_asr_caption_lags.append(time_translation - time_asr)

    if not all_asr_caption_lags:
        return 0.0

    return mean(all_asr_caption_lags) if all_asr_caption_lags else 0.0


def score_incremental_caption_lag(partial_translations):
    """Measures the time between caption updates, *not* including the
    time it takes to see the initial caption per putterance."""
    all_lags = []
    for utterance_translation in partial_translations:
        prev_caption_timestamp_and_text = (None, None)
        for timestamp, translation in utterance_translation:
            translation = translation.strip()
            if not translation:
                continue

            # Don't include initial_caption_lag in this metric.
            if (
                prev_caption_timestamp_and_text[0] is not None
                and translation != prev_caption_timestamp_and_text[1]
            ):
                all_lags.append(timestamp - prev_caption_timestamp_and_text[0])

            prev_caption_timestamp_and_text = (timestamp, translation)
    return mean(all_lags) if all_lags else 0.0


def score_stability(partial_translations, target_language):
    """Measures the amount of word erasure during realtime translation."""
    tokenizer = get_tokenizer(target_language)
    erased_tokens = 0
    final_target_tokens = 0

    for utterance_partial_translations in partial_translations:
        if len(utterance_partial_translations) == 0:
            continue
        prev_translation = tokenizer.tokenize(utterance_partial_translations[0][1])
        translation = []

        for i in range(1, len(utterance_partial_translations)):
            translation = tokenizer.tokenize(utterance_partial_translations[i][1])
            common_prefix_length = len(
                os.path.commonprefix([translation, prev_translation])
            )
            erased_tokens += len(prev_translation) - common_prefix_length
            prev_translation = translation

        final_target_tokens += len(translation)

    return erased_tokens / max(final_target_tokens, 1)


def score_latency(
    references, reference_wavs, partial_translations, target_language="en-US"
):
    """Measures the "final" translation lag after all corrections have been made."""
    logger = logging.getLogger("evaluation")
    tokenizer = get_tokenizer(target_language)

    min_len = min(len(partial_translations), len(references))

    if len(partial_translations) != len(references):
        logger.warning(
            f"Found {len(references)} references, {len(partial_translations)} partial "
            + f"translations. Evaluating only the first {min_len}"
        )

    partial_translations = partial_translations[:min_len]
    references = references[:min_len]

    # Make case insensitive and tokenize
    partial_translations_tokenized = [
        [(t_time, tokenizer.tokenize(t.upper())) for t_time, t in transcript]
        for transcript in partial_translations
    ]
    references = [tokenizer.tokenize(r.upper()) for r in references]

    # Compute total lag
    output_words, total_lag = 0, 0

    for reference, (_, reference_wav), partial_translation in zip(
        references, reference_wavs, partial_translations_tokenized
    ):
        if len(partial_translation) == 0:
            continue

        final_time, final_translation = partial_translation[-1]
        reference_duration = get_duration_seconds(reference_wav)

        for j in range(1, len(final_translation) + 1):
            # Compare a time a word was finalized in the output
            # to the time its corresponding word was uttered
            finalization_time = get_finalization_time(
                final_translation, j, partial_translation
            )
            original_token = int(j * len(reference) / len(final_translation))
            original_time = get_token_time(
                original_token, reference, reference_duration
            )

            total_lag += max(0, finalization_time - original_time)
            output_words += 1

    return total_lag / max(1, output_words)


def get_token_time(token_index, sentence, duration):
    """
    Linearly interpolate to guess the time a token was utterred
    """
    sentence_len = max(len(sentence), 1)

    return token_index / sentence_len * duration


def get_finalization_time(final_transcript, j, partial_transcripts):
    """
    Return the first time such that the first j tokens of the transcript
    are the same for all following transcripts.
    """
    prefix = final_transcript[:j]
    partial_time = 0

    for partial_time, partial_transcript in reversed(partial_transcripts):
        if partial_transcript[:j] != prefix:
            return partial_time

    return partial_time
