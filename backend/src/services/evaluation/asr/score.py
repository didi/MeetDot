import collections
from dataclasses import dataclass
import logging
import re
from typing import List, Tuple, Optional, Union, Dict

import jiwer
from services.evaluation.score import EvaluationScore
from services.normalization import get_normalizer, NORMALIZER_SUPPORTED_LANGUAGES
from services.tokenizer import get_tokenizer
from utils import get_duration_seconds, safe_divide


@dataclass
class SpeechRecognitionEvaluationScore(EvaluationScore):
    wer: float
    transcription_lag: float
    language_id_accuracy: float
    initial_asr_lag: float


# Do not include 一, it has other meanings in sentences.
CHINESE_NUMERIC_CHARACTERS = "零二三四五六七八九十百千万1234567890"


def score(references, predictions, reference_languages):
    logger = logging.getLogger("evaluation")

    min_len = min(len(predictions), len(references))

    if len(predictions) == 0:
        raise ValueError("Empty ASR predictions")

    if len(predictions) != len(references):
        logger.warning(
            f"Found {len(references)} references, {len(predictions)} transcripts."
            + f"Evaluating only the first {min_len}"
        )
    predictions = predictions[:min_len]
    references = references[:min_len]
    num_refs = len(references)

    for i, (reference, prediction, language) in enumerate(
        zip(references, predictions, reference_languages)
    ):
        if language in NORMALIZER_SUPPORTED_LANGUAGES:
            normalizer = get_normalizer(language)
            references[i] = normalizer.normalize(references[i])
            predictions[i] = normalizer.normalize(predictions[i])

        if language == "zh":
            # Character split references and predictions to compute CER for chinese
            references[i] = " ".join(list(references[i].replace(" ", "")))
            predictions[i] = " ".join(list(predictions[i].replace(" ", "")))

    transformation = jiwer.Compose(
        [
            jiwer.ToUpperCase(),
            jiwer.RemoveKaldiNonWords(),
            jiwer.Strip(),
            jiwer.RemovePunctuation(),
            jiwer.RemoveMultipleSpaces(),
            jiwer.SentencesToListOfWords(word_delimiter=" "),
        ]
    )

    # Compute WER score
    wer = jiwer.wer(
        references,
        predictions,
        truth_transform=transformation,
        hypothesis_transform=transformation,
    )

    return wer * 100, num_refs


def score_latency(references, reference_utterances, partial_transcripts):
    """
    Return the latency score, measured as the average time between a
    token being uttered and the time it is finalized in the output
    """
    logger = logging.getLogger("evaluation")

    if len(partial_transcripts) != len(references):
        min_len = min(len(partial_transcripts), len(references))
        logger.warning(
            f"Found {len(references)} references, {len(partial_transcripts)} partial"
            + f" transcripts. Evaluating only the first {min_len}"
        )
        partial_transcripts = partial_transcripts[:min_len]
        references = references[:min_len]

    # Compute total lag
    output_words, total_lag = 0, 0

    for reference, (_, language, reference_wav), partial_transcript in zip(
        references, reference_utterances, partial_transcripts
    ):
        if len(partial_transcript) == 0:
            continue

        # Make case insensitive and tokenize
        tokenizer = get_tokenizer(language)
        reference = tokenizer.tokenize(reference.upper())
        partial_transcript_tokenized = [
            (t_time, tokenizer.tokenize(t.upper())) for t_time, t in partial_transcript
        ]

        final_time, final_transcript = partial_transcript_tokenized[-1]
        reference_duration = get_duration_seconds(reference_wav)

        for j in range(len(final_transcript)):
            # Compare time a word was finalized in the output to
            # the time it was uttered
            finalization_time = get_finalization_time(
                final_transcript, j, partial_transcript_tokenized
            )
            original_token = int(j * len(reference) / len(final_transcript))
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

    return (token_index + 1) / max(1, len(sentence)) * duration


def get_finalization_time(
    final_transcript: List[str], j: int, partial_transcripts: List[Tuple[float, str]]
):
    """
    Return the first time such that tokens up to and including index j of
    the transcript are the same for all following transcripts.
    """
    prefix = final_transcript[: j + 1]
    previous_time = 0
    partial_time = 0

    for partial_time, partial_transcript in reversed(partial_transcripts):
        if partial_transcript[: j + 1] != prefix:
            return previous_time
        previous_time = partial_time

    return partial_time


def score_name_f1(
    gold_transcript: List[str],
    predictions: List[str],
    names: List[List[str]],
    language="en-US",
):
    """
    Measure the f1 of recognizing entity names, such as Google, Kevin,
    etc., in the dataset. Case-insensitive.
    """

    def compute_name_occurrences(token_list, name_list):
        """
        In the "token_list", find occurrences of each name in the
        "name_list". Return number of total name occurrences and the occurred
        names.
        """
        # sort names by token length. longer names first.
        name_list = sorted(
            [n.split() for n in name_list], key=lambda x: len(x), reverse=True
        )

        # use a set to store token index of checked names. this prevents over
        # counting those names which are substrings of other names.
        occurred_name_idx = set()
        name_occurrence = 0
        occurred_names = set()

        # count name occurrences
        for name in name_list:
            i = 0
            while i < len(token_list):
                if token_list[i] == name[0]:
                    n = 1
                    while (
                        (n < len(name))
                        and (i + n < len(token_list))
                        and (token_list[i + n] == name[n])
                    ):
                        n += 1

                    if n == len(name):
                        # only count names that have not been checked.
                        idx = set(range(i, i + n))
                        if not idx.intersection(occurred_name_idx):
                            name_occurrence += 1
                            occurred_name_idx |= idx
                            occurred_names.add(" ".join(name))
                        i += n
                    else:
                        i += 1
                else:
                    i += 1
        return name_occurrence, occurred_names

    if not names:
        name_precision = 0
        name_recall = 0
        name_f1 = 0
        gold_name_count = 0
        sys_name_count = 0
        name_hit = 0
    else:
        # load the tokenizer to tokenize sentence into a list of tokens
        tokenizer = get_tokenizer(language)

        # generate a list of unique names from the test set. it's used for
        # counting system recognized names, which is then used for computing
        # precision
        unique_names = list({_n for n in names for _n in n})

        # compute name recognition precision, recall, f1
        gold_name_count = 0
        sys_name_count = 0
        name_hit = 0
        for gold, pred, n in zip(gold_transcript, predictions, names):
            pred_tokens = tokenizer.tokenize(
                pred.lower().replace(",", "").replace(".", "")
            )
            gold_tokens = tokenizer.tokenize(
                gold.lower().replace(",", "").replace(".", "")
            )

            # count the number of occurrences of the gold name in the
            # system and gold tokenized sentence.
            name_hit += compute_name_occurrences(pred_tokens, n)[0]
            gold_n = compute_name_occurrences(gold_tokens, n)[0]
            gold_name_count += gold_n

            # count the number of occurrences of all names in the system output.
            sys_n, sys_names = compute_name_occurrences(pred_tokens, unique_names)
            sys_name_count += sys_n

        name_recall = safe_divide(name_hit, gold_name_count) * 100
        name_precision = safe_divide(name_hit, sys_name_count) * 100
        name_f1 = safe_divide(
            2 * name_precision * name_recall, name_precision + name_recall
        )

    return (
        name_precision,
        name_recall,
        name_f1,
        gold_name_count,
        sys_name_count,
        name_hit,
    )


def score_language_id_accuracy(
    reference_language: Union[str, Dict[str, List[Tuple[float, str]]]],
    reference_durations: Dict[str, float],
    detected_languages: Dict[str, List[Tuple[float, str]]],
):
    """
    Calculates overlap between the reference language, and the
    languages detected by the language ID system

    Reference language can either be a constant string, or it can be
    a list of intervals with language codes per utterance
    """
    overlap_time = 0
    total_time = 0

    for utterance_id, languages in detected_languages.items():
        for i in range(len(languages)):
            start_time, detected_language = languages[i]
            end_time = (
                languages[i + 1][0]
                if i + 1 < len(languages)
                else reference_durations[utterance_id]
            )
            time_interval = end_time - start_time
            total_time += time_interval
            if type(reference_language) is str:
                # Constant language ID
                overlap_time += time_interval * (
                    detected_language == reference_language
                )
            else:
                # Language ID specified as intervals per utterance
                ref_languages = reference_language[utterance_id]
                for j in range(len(ref_languages)):
                    ref_start_time, ref_language = ref_languages[j]
                    ref_end_time = (
                        ref_languages[j + 1][0]
                        if j + 1 < len(ref_languages)
                        else reference_durations[utterance_id]
                    )
                    interval_overlap = max(
                        0, min(end_time, ref_end_time) - max(start_time, ref_start_time)
                    )
                    overlap_time += interval_overlap * (
                        detected_language == ref_language
                    )

    return overlap_time / total_time if total_time else 0.0


def score_initial_asr_lag(partial_transcripts):
    """Measures the time between when we start playback of the wav file and
    when the asr system issues its first non-empty transcription."""
    initial_lags = []
    for per_utterance_transcripts in partial_transcripts:
        if not per_utterance_transcripts:
            continue
        lag = None
        for timestamp, transcript in per_utterance_transcripts:
            lag = timestamp
            if transcript.strip():
                break
        initial_lags.append(lag)

    if not initial_lags:
        return 0.0
    return float(sum(initial_lags)) / len(initial_lags)


def score_wer_by_speaker(references, predictions, speakers, language):
    # split references/predictions by speaker
    references_per_speaker = collections.defaultdict(list)
    predictions_per_speaker = collections.defaultdict(list)
    for r, p, s in zip(references, predictions, speakers):
        if not s:
            continue
        references_per_speaker[s].append(r)
        predictions_per_speaker[s].append(p)

    wer_per_speaker = {}
    for s in references_per_speaker.keys():
        wer, _ = score(
            references_per_speaker[s],
            predictions_per_speaker[s],
            [language] * len(references_per_speaker[s]),
        )
        wer_per_speaker[s] = (wer, len(references_per_speaker[s]))

    # sort wer by speaker
    sorted_wer_per_speaker = sorted(
        wer_per_speaker.items(), key=lambda x: x[1][0], reverse=True
    )

    return sorted_wer_per_speaker
