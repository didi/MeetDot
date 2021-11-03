import functools
import logging
import time
import wave
from pathlib import Path
from typing import Dict, List, Tuple
from unittest import mock

import gevent
import tqdm
from gevent.pool import Pool
from services.asr import SpeechRecognitionRequest, SpeechRecognitionResponse
from services.captioning import CaptioningRequest, CaptioningResponse
from services.captioning.utils import DELIMITERS, combine_utterances, get_word_separator
from services.evaluation.asr.evaluate import (
    load_partial,
    load_transcripts,
    save_partial,
)
from services.evaluation.asr.score import score_initial_asr_lag
from services.evaluation.logs import save_wandb_logs
from services.evaluation.translation.evaluate import (
    load_predictions as load_translations,
)
from services.post_translation import PostTranslationRequest, PostTranslationResponse
from services.speech_translation import (
    SpeechTranslationRequest,
    SpeechTranslationService,
)

from .score import (
    SpeechTranslationEvaluationScore,
    score_bleu,
    score_latency,
    score_stability,
    score_wer,
    score_wer_by_speaker,
    score_len_ratio,
    score_name_f1,
    score_word_burstiness,
    score_initial_caption_lag,
    score_initial_asr_caption_lag,
    score_incremental_caption_lag,
)
from .test_set import SpeechTranslationDataset
from utils import write_list_to_file


def save_initial_caption_times(utterance_id, initial_caption_time, output_csv):
    with open(output_csv, "a") as out:
        out.write(f"{utterance_id},{initial_caption_time:.2f}\n")


# TODO(scotfang): Remove serialization of initial_caption_times, it's unnecessary because
#                 timestamps in partial translations already store this information.
def load_initial_caption_times(input_csv):
    initial_caption_times = []
    with open(input_csv, "r") as in_f:
        for line in in_f:
            line = line.strip()

            if line:
                utterance_id, time_in_seconds = line.split(",")
                initial_caption_times.append(float(time_in_seconds))

    return initial_caption_times


def infer(
    speech_translator,
    dataset: SpeechTranslationDataset,
    output_files: Tuple[Path, Path, Path, Path, Path],
    first_n: int = -1,
    num_workers: int = 1,
    no_simulate_realtime: bool = True,
):
    logger = logging.getLogger("evaluation")

    # Set up output_files
    (
        transcript_path,
        translation_path,
        partial_transcript_path,
        partial_translation_path,
        initial_caption_times_output_path,
    ) = output_files

    # Clear partial output files, just in case there's something already there
    open(partial_transcript_path, "w").close()
    open(partial_translation_path, "w").close()
    open(initial_caption_times_output_path, "w").close()

    partial_transcripts, partial_translations = {}, {}
    transcript_prefixes = {}
    complete_utterances = {}

    # Set up event listeners
    transcript_listener = functools.partial(
        on_transcript,
        transcripts=partial_transcripts,
        prefixes=transcript_prefixes,
        language=dataset.source_language,
    )
    speech_translator.add_listener("asr", transcript_listener)

    caption_listener = functools.partial(
        on_caption,
        translations=partial_translations,
        completed_utterances=complete_utterances,
    )
    speech_translator.add_listener("captioning", caption_listener)

    dataset_iterator = dataset.wav_files

    if first_n > 0:
        dataset_iterator = dataset_iterator[:first_n]

    # Run inference on dataset, distributed across N workers
    pool = Pool(num_workers)
    infer_utterance_partial = functools.partial(
        infer_utterance,
        source_language=dataset.source_language,
        speech_translator=speech_translator,
        partial_transcripts=partial_transcripts,
        partial_translations=partial_translations,
        no_simulate_realtime=no_simulate_realtime,
    )
    res = pool.imap(infer_utterance_partial, dataset_iterator)
    translations = sorted(
        [t for t in tqdm.tqdm(res, total=len(dataset_iterator))],
        key=lambda t: t[0],
    )
    (
        _utterance_id,
        final_transcripts,
        all_partial_transcripts,
        final_translations,
        all_partial_translations,
        initial_caption_times,
    ) = map(list, zip(*translations))

    with open(transcript_path, "w", encoding="utf-8") as transcript_file, open(
        translation_path, "w", encoding="utf-8"
    ) as translation_file:

        for (
            utterance_id,
            final_transcript,
            partial_transcripts,
            final_translation,
            partial_translations,
            initial_caption_time,
        ) in translations:
            transcript_file.write(f"{utterance_id} {final_transcript}\n")
            translation_file.write(final_translation + "\n")
            save_partial(utterance_id, partial_transcripts, partial_transcript_path)
            save_partial(utterance_id, partial_translations, partial_translation_path)
            save_initial_caption_times(
                utterance_id, initial_caption_time, initial_caption_times_output_path
            )

    logger.info("Done translating dataset!")

    return (
        final_transcripts,
        all_partial_transcripts,
        final_translations,
        all_partial_translations,
        initial_caption_times,
    )


def infer_utterance(
    utterance,
    speech_translator,
    partial_transcripts,
    partial_translations,
    source_language,
    no_simulate_realtime,
):
    utterance_id, wav_path = utterance
    partial_transcripts[utterance_id] = []
    partial_translations[utterance_id] = []
    chunk_size = speech_translator.config.asr.chunk_size

    # Stream wav file into speech translation service
    speech_translator.start_listening(utterance_id, source_language)
    initial_wav_time = None
    with wave.open(wav_path) as wav_file:
        read_frames = 0
        start_time = time.time()
        asr_config = speech_translator.config.asr
        total_frames = wav_file.getnframes()

        while read_frames < total_frames:
            if initial_wav_time is None:
                initial_wav_time = start_time
            num_frames = min(chunk_size, total_frames - read_frames)
            # Sleep for duration of the chunk, to simulate real-time input
            if not no_simulate_realtime:
                gevent.sleep(num_frames / asr_config.sample_rate_hertz)
            chunk = wav_file.readframes(num_frames)
            speech_translator(
                SpeechTranslationRequest(session_id=utterance_id, chunk=chunk)
            )
            read_frames += num_frames

    speech_translator.stop_listening(utterance_id)

    # Collect and save the final transcripts
    utterance_transcripts = partial_transcripts[utterance_id]
    final_transcript = (
        utterance_transcripts[-1][1] if len(utterance_transcripts) else ""
    )

    # Collect the partial transcripts
    partial_transcript = [
        (timestamp - start_time, transcript)
        for timestamp, transcript in partial_transcripts[utterance_id]
    ]

    # Collect and save the final translations
    utterance_translations = partial_translations[utterance_id]
    final_translation = (
        utterance_translations[-1][1] if len(utterance_translations) else ""
    )

    # Collect the partial translations (translations before the final)
    partial_translation = [
        (timestamp - start_time, translation)
        for timestamp, translation in partial_translations[utterance_id]
    ]

    initial_caption_time = -1

    if initial_wav_time is not None and partial_translations:
        for timestamp, translation in partial_translations[utterance_id]:
            if translation:
                initial_caption_time = timestamp - initial_wav_time

                break

    return (
        utterance_id,
        final_transcript,
        partial_transcript,
        final_translation,
        partial_translation,
        initial_caption_time,
    )


def on_transcript(
    request: SpeechRecognitionRequest,
    response: SpeechRecognitionResponse,
    language,
    prefixes,
    transcripts,
):
    prefixes.setdefault(request.session_id, [])
    utterances = prefixes[request.session_id] + [response.transcript]
    delimiter = "。" if language == "zh" else ". "
    transcripts[request.session_id].append((time.time(), delimiter.join(utterances)))

    if response.is_final:
        prefixes[request.session_id].append(response.transcript.rstrip(".。").rstrip())


def on_caption(
    request: CaptioningRequest,
    response: CaptioningResponse,
    completed_utterances: Dict[str, List[str]],
    translations: Dict[str, List[Tuple[float, str]]],
):
    """
    Upon receiving a caption response, determine the translation
    string that has been displayed so far.

    To do so, first it looks at the input and previous complete utterances,
    and combines them into a string, assuming the entire utterance will have
    been displayed. Then, it checks to see that the end of what is displayed
    matches the end of the input - if it doesn't, then it replaces the final
    sentence with the final sentence of what is displayed.

    This still does not cover every single possible case of captioning system
    behaviour, but it covers the vast majority.

    TODO: there's a race condition here that causes utterances to occasionally
    get dropped, but it only occurs with many workers and multiple evaluators
    running in parallel.
    """
    # First, assume all of the input has been displayed on the screen
    prev_utterances = completed_utterances.get(request.session_id, [])
    input_translation = combine_utterances(
        request.target_language,
        prev_utterances,
        request.utterance,
        request.utterance_complete,
    )

    word_separator = get_word_separator(request.target_language)
    # Then, see if what is displayed matches the end of the input
    displayed_string = word_separator.join(list(filter(len, response.lines)))

    if not input_translation.endswith(displayed_string) or len(displayed_string) == 0:
        # If ends don't match, use last utterance of what's been displayed
        # instead of last utterance of input
        input_start, input_final = split_sentences(input_translation)
        _, displayed_final = split_sentences(displayed_string)

        overlap_index = 0

        while overlap_index < len(input_final):
            # Find the first index where the last sentence displayed overlaps with the
            # last sentence of the input

            if (
                input_final[overlap_index : overlap_index + len(displayed_final)]
                == displayed_final
            ):
                break
            overlap_index += 1

        input_final = input_final[: overlap_index + len(displayed_final)]
        partial_translation = word_separator.join(
            list(filter(len, (input_start, input_final)))
        )
    else:
        partial_translation = input_translation

    if request.utterance_complete:
        completed_utterances.setdefault(request.session_id, [])
        completed_utterances[request.session_id].append(request.utterance)

    # Save partial translations to output
    translations.setdefault(request.session_id, [])
    translations[request.session_id].append((time.time(), partial_translation))


def split_sentences(sentences: str):
    """
    Split a string s into two strings: the first N-1 sentences and the last N
    """
    last_delimiter = max(sentences.rfind(delim) for delim in DELIMITERS) + 1

    return sentences[:last_delimiter], sentences[last_delimiter:]


def evaluate_dataset(
    config,
    dataset,
    output_dir,
    num_workers,
    first_n=-1,
    overwrite=False,
    no_simulate_realtime=False,
    only_predict=False,
):
    logger = logging.getLogger("evaluation")

    source_output_path = output_dir / f"{dataset.name}.{dataset.source_language}.txt"
    target_output_path = output_dir / f"{dataset.name}.{dataset.target_language}.txt"
    partial_transcript_output_path = (
        output_dir / f"{dataset.name}.partial.{dataset.source_language}.txt"
    )
    partial_translation_output_path = (
        output_dir / f"{dataset.name}.partial.{dataset.target_language}.txt"
    )
    source_reference_filename = (
        output_dir / f"{dataset.name}.ref.{dataset.source_language}.txt"
    )
    target_reference_filename = (
        output_dir / f"{dataset.name}.ref.{dataset.target_language}.txt"
    )
    initial_caption_times_output_path = (
        output_dir / f"{dataset.name}.initial_caption_times.csv"
    )
    source_name_reference_filename = output_dir / f"{dataset.name}.ref.names.txt"

    output_files = (
        source_output_path,
        target_output_path,
        partial_transcript_output_path,
        partial_translation_output_path,
        initial_caption_times_output_path,
    )

    if all(f.exists() for f in output_files) and not overwrite:
        logger.info(
            f"Predicted transcripts and translations found at {source_output_path}"
            + f" and {target_output_path}, evaluating those"
        )
        transcripts = load_transcripts(source_output_path, first_n=first_n)
        translations = load_translations(target_output_path, first_n=first_n)
        partial_transcripts = load_partial(
            partial_transcript_output_path, first_n=first_n
        )
        partial_translations = load_partial(
            partial_translation_output_path, first_n=first_n
        )
        initial_caption_times = load_initial_caption_times(
            initial_caption_times_output_path
        )
    else:
        logger.info(
            "Predicted transcripts and translations not found at"
            + f" {source_output_path} and {target_output_path}"
            + ", computing predictions"
        )
        logger.debug("Loading speech translator")

        mock_logger = mock.Mock()
        mock_logger.log_dir = output_dir / "logs"
        mock_logger.log_dir.mkdir(parents=True, exist_ok=True)

        speech_translator = SpeechTranslationService(
            config=config,
            logger=mock_logger,
            languages=lambda _: {dataset.target_language},
            start_time=time.time(),
        )
        logger.debug("Loaded speech translator")

        (
            transcripts,
            partial_transcripts,
            translations,
            partial_translations,
            initial_caption_times,
        ) = infer(
            speech_translator,
            dataset,
            output_files,
            first_n,
            num_workers,
            no_simulate_realtime,
        )

        # Save ASR, translation, and names reference.
        # This serialization is just for debugging, it's not required for non-overwrite mode.
        if dataset.transcripts:
            write_list_to_file(
                input_list=dataset.transcripts, output_path=source_reference_filename
            )
            logger.debug("Serialized dataset reference transcripts")
        if dataset.translations:
            write_list_to_file(
                input_list=dataset.translations, output_path=target_reference_filename
            )
            logger.debug("Serialized dataset reference translations")
        if dataset.names:
            write_list_to_file(
                input_list=["\t".join(n) for n in dataset.names],
                output_path=source_name_reference_filename,
            )
            logger.debug("Serialized dataset reference names")

    if only_predict:
        return None

    if first_n > 0:
        dataset.transcripts = dataset.transcripts[:first_n]
        dataset.translations = dataset.translations[:first_n]

    wer, num_refs = score_wer(
        dataset.transcripts,
        transcripts,
        [dataset.source_language] * len(dataset.transcripts),
    )

    logger.info(
        f"Computing scores on {dataset.name} for {dataset.source_language}"
        + f"-> {dataset.target_language}..."
    )

    if dataset.source_language == "zh":
        logger.info(f"CER: {wer:.1f}%")
    else:
        logger.info(f"WER: {wer:.1f}%")

    if dataset.speakers:
        wer_per_speaker = score_wer_by_speaker(
            dataset.transcripts,
            transcripts,
            dataset.speakers,
            language=dataset.source_language,
        )
        if wer_per_speaker:
            if dataset.source_language == "zh":
                logger.info(
                    "CER per speaker (number of transcripts for each "
                    "speaker is shown in parenthesis): "
                )
            else:
                logger.info(
                    "WER per speaker (number of transcripts for each "
                    "speaker is shown in parenthesis): "
                )
            for item in wer_per_speaker:
                logger.info(f"  {item[0]}: {item[1][0]:.1f} ({item[1][1]})")

    asr_len_ratio = score_len_ratio(dataset.transcripts, transcripts)
    logger.info(f"ASR len_ratio: {asr_len_ratio:.2f}")

    translation_len_ratio = score_len_ratio(
        dataset.translations,
        translations,
        [dataset.target_language] * len(dataset.translations),
        normalize=True,
    )
    logger.info(f"Translation len_ratio: {translation_len_ratio:.2f}")

    bleu, _ = score_bleu(
        dataset.translations, translations, target_language=dataset.target_language
    )
    logger.info(f"BLEU score {bleu.score:.1f}")

    normalized_erasure = score_stability(
        partial_translations, target_language=dataset.target_language
    )
    logger.info(f"Normalized erasure {normalized_erasure:.1f}")
    if no_simulate_realtime:
        latency = -1
    else:
        latency = score_latency(
            dataset.transcripts,
            dataset.wav_files,
            partial_translations,
            target_language=dataset.target_language,
        )
    logger.info(f"Translation lag {latency:.2f}s")

    if no_simulate_realtime:
        initial_asr_lag = -1
        initial_caption_lag = -1
        initial_asr_caption_lag = -1
        incremental_caption_lag = -1
    else:
        initial_asr_lag = score_initial_asr_lag(partial_transcripts)
        initial_caption_lag = score_initial_caption_lag(initial_caption_times)
        initial_asr_caption_lag = score_initial_asr_caption_lag(
            partial_transcripts, partial_translations
        )
        incremental_caption_lag = score_incremental_caption_lag(partial_translations)
    logger.info(f"Initial asr lag {initial_asr_lag:.2f}s")
    logger.info(f"Initial caption lag {initial_caption_lag:.2f}s")
    logger.info(f"Initial asr_caption lag {initial_asr_caption_lag:.2f}s")
    logger.info(f"Incremental caption lag {incremental_caption_lag:.2f}s")

    max_word_burstiness, mean_word_burstiness = score_word_burstiness(
        partial_translations, dataset.target_language
    )
    logger.info(f"Max Word Burstiness: {max_word_burstiness:.2f} words")
    logger.info(f"Mean Word Burstiness: {mean_word_burstiness:.2f} words")

    (
        name_precision,
        name_recall,
        name_f1,
        gold_name_count,
        sys_name_count,
        name_hit,
    ) = score_name_f1(dataset.transcripts, transcripts, dataset.names)
    logger.info(
        f"ASR name p/r/f1 on {dataset.name}:"
        + f"{name_precision:.1f}% / {name_recall:.1f}% / {name_f1:.1f}%."
    )
    logger.info(
        f"ASR gold name: {gold_name_count},"
        + f"sys recognized names: {sys_name_count}, correctly recognized names: {name_hit}"
    )

    return (
        SpeechTranslationEvaluationScore(
            wer=wer,
            wer_per_speaker=str(wer_per_speaker),
            bleu=bleu.score,
            normalized_erasure=normalized_erasure,
            translation_lag=latency,
            initial_asr_lag=initial_asr_lag,
            initial_caption_lag=initial_caption_lag,
            initial_asr_caption_lag=initial_asr_caption_lag,
            incremental_caption_lag=incremental_caption_lag,
            max_burstiness=max_word_burstiness,
            mean_burstiness=mean_word_burstiness,
            name_precision=name_precision,
            name_recall=name_recall,
            name_f1=name_f1,
            asr_len_ratio=asr_len_ratio,
            translation_len_ratio=translation_len_ratio,
        ),
        num_refs,
    )


def evaluate(
    name,
    config,
    dataset_dir,
    datasets,
    output_dir,
    first_n=-1,
    num_workers=1,
    overwrite=False,
    save_wandb=True,
    no_simulate_realtime=False,
    only_predict=False,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("evaluation")

    logger.info("Evaluating speech translation")

    # Load test set

    for dataset_name in datasets:
        test_set = SpeechTranslationDataset(dataset_dir, dataset_name)
        eval_output = evaluate_dataset(
            config,
            test_set,
            output_dir,
            num_workers,
            first_n=first_n,
            overwrite=overwrite,
            no_simulate_realtime=no_simulate_realtime,
            only_predict=only_predict,
        )
        if not only_predict:
            dataset_score, num_refs = eval_output
            dataset_score.save(output_dir / f"{dataset_name}.json")

            if save_wandb:
                # Log evaluation results to W&B
                save_wandb_logs(
                    config,
                    test_set.to_dict(),
                    num_refs,
                    dataset_score,
                    name=f"{name}-{dataset_name}",
                    group="st",
                )
