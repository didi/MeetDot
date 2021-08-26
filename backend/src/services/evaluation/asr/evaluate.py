import copy
from datetime import datetime
import functools
import logging
import time
import wave
from pathlib import Path
from typing import List, Tuple
from unittest import mock

import gevent
import tqdm
from gevent.pool import Pool
from services.asr import (
    LanguageIdRequest,
    LanguageIdResponse,
    SpeechRecognitionConfig,
    SpeechRecognitionRequest,
    SpeechRecognitionResponse,
    SpeechRecognitionService,
)
from services.evaluation.logs import save_wandb_logs
from utils import start_thread, get_duration_seconds

from .language_id import parse_language_id_block
from .score import (
    SpeechRecognitionEvaluationScore,
    score,
    score_latency,
    score_language_id_accuracy,
    score_initial_asr_lag,
)
from .test_set import SpeechRecognitionDataset


def infer(
    make_recognizer,
    dataset: SpeechRecognitionDataset,
    partial_transcripts,
    detected_languages,
    start_times,
    output_paths: Tuple[Path, Path, Path],
    first_n: int,
    num_workers: int,
    no_simulate_realtime: bool,
):
    final_transcripts = []
    all_partial_transcripts = []

    output_path, partial_output_path, language_id_path = output_paths

    # Clear partial output file, just in case there's something already there
    open(partial_output_path, "w").close()
    if first_n > 0:
        dataset_iterator = dataset.utterances[:first_n]
    else:
        dataset_iterator = dataset.utterances

    # Run inference on dataset, distributed across N workers
    pool = Pool(num_workers)
    infer_utterance_partial = functools.partial(
        infer_utterance,
        make_recognizer=make_recognizer,
        partial_transcripts=partial_transcripts,
        detected_languages=detected_languages,
        start_times=start_times,
        no_simulate_realtime=no_simulate_realtime,
    )
    res = pool.imap(infer_utterance_partial, dataset_iterator)
    transcripts = sorted(
        [t for t in tqdm.tqdm(res, total=len(dataset_iterator))],
        key=lambda t: t[0],
    )
    utterance_ids, final_transcripts, all_partial_transcripts = map(
        list, zip(*transcripts)
    )

    # Save outputs - partial transcripts
    with open(output_path, "w", encoding="utf-8") as output_file:
        for utterance_id, final_transcript, partial_transcripts in transcripts:
            output_file.write(f"{utterance_id} {final_transcript}\n")
            save_partial(utterance_id, partial_transcripts, partial_output_path)

    # Save outputs - language ID predictions
    save_detected_languages(detected_languages, language_id_path)

    return final_transcripts, all_partial_transcripts


def infer_utterance(
    utterance,
    make_recognizer,
    partial_transcripts,
    detected_languages,
    start_times,
    no_simulate_realtime,
):
    utterance_id, initial_language, wav_path = utterance
    recognizer = make_recognizer(initial_language)
    partial_transcripts[utterance_id] = []
    detected_languages[utterance_id] = [(0.0, initial_language)]
    thread = start_thread(recognizer.run)
    language_id_thread = start_thread(recognizer.run_language_detect)

    # Load wav file
    with wave.open(wav_path) as wav_file:
        i = 0

        start_times[utterance_id] = time.time()

        while i < wav_file.getnframes():
            # Pass chunk by chunk to recognizer
            chunk = wav_file.readframes(recognizer.config.chunk_size)
            recognizer(SpeechRecognitionRequest(session_id=utterance_id, chunk=chunk))
            i += recognizer.config.chunk_size
            # Sleep for duration of the chunk, to not overwhelm the streaming ASR
            if not no_simulate_realtime:
                gevent.sleep(
                    recognizer.config.chunk_size / recognizer.config.sample_rate_hertz
                )

    # Clean up recognizer
    recognizer.end_utterance()
    recognizer.wait_for_final()
    thread.join()
    language_id_thread.join()

    # Collect and save partial transcripts
    partial_transcript = [
        (timestamp - start_times[utterance_id], r)
        for timestamp, r in partial_transcripts[utterance_id]
    ]

    # Collect and save the final transcripts
    utterance_transcripts = partial_transcripts[utterance_id]
    final_transcript = (
        utterance_transcripts[-1][1] if len(utterance_transcripts) else ""
    )

    return utterance_id, final_transcript, partial_transcript


def load_transcripts(output_path: Path, first_n: int = -1):
    with open(output_path) as output_file:
        # Strip off the utterance ID from the saved file
        predictions = []

        for line in output_file:
            predictions.append(" ".join(line.strip().split(" ")[1:]))

            if first_n > 0 and len(predictions) >= first_n:
                break

    return predictions


def load_partial(output_path: Path, first_n: int = -1):
    partial_transcripts: List[List[Tuple[float, str]]] = []
    with open(output_path) as f:
        for line in f:
            line = line.rstrip("\n")

            if line.startswith("### ") and line.endswith(" ###"):
                partial_transcripts.append([])
            else:
                split_line = line.split(": ")
                timestamp = split_line[0]
                transcript = split_line[1] if len(line) > 1 else ""
                partial_transcripts[-1].append((float(timestamp), transcript))

            if first_n > 0 and len(partial_transcripts) > first_n:
                # Only break after the Nth partial transcript is complete
                partial_transcripts = partial_transcripts[:-1]

    return partial_transcripts


def save_partial(
    utterance_id: str,
    partial_predictions: List[Tuple[float, str]],
    partial_output_path: Path,
):
    with open(partial_output_path, "a", encoding="utf-8", buffering=1) as f:
        f.write(f"### {utterance_id} ###\n")

        for timestamp, transcript in partial_predictions:
            f.write(f"{timestamp:.2f}: {transcript}\n")


def load_detected_languages(output_path: Path, first_n: int = -1):
    detected_languages = {}

    # Parse language ID files
    with open(output_path) as language_id_file:
        block = []
        for line in language_id_file:
            line = line.strip()
            if line == "":
                # Parse block
                file_id, intervals = parse_language_id_block(block)
                detected_languages[file_id] = intervals
                block = []

                # Stop after first N if necessary
                if first_n > 0 and len(detected_languages) >= first_n:
                    break
            else:
                block.append(line)
        if len(block):
            file_id, intervals = parse_language_id_block(block)
        detected_languages[file_id] = intervals

    return detected_languages


def save_detected_languages(detected_languages, output_path: Path):
    detected_languages_sorted = sorted(detected_languages.items(), key=lambda x: x[0])
    with open(output_path, "w") as language_id_file:
        for utterance_id, intervals in detected_languages_sorted:
            language_id_file.write(f"{utterance_id}\n")
            for interval, language_id in intervals:
                interval_time_str = datetime.fromtimestamp(interval).strftime(
                    "%M:%S.%f"
                )
                language_id_file.write(f"{interval_time_str} - {language_id}\n")
            language_id_file.write("\n")


def on_transcript(
    request: SpeechRecognitionRequest,
    response: SpeechRecognitionResponse,
    prefixes,
    transcripts,
):
    prefixes.setdefault(request.session_id, [])
    utterances = prefixes[request.session_id] + [response.transcript]
    delimiter = "。" if response.language == "zh" else ". "

    transcripts[request.session_id].append((time.time(), delimiter.join(utterances)))

    if response.is_final:
        prefixes[request.session_id].append(response.transcript.rstrip("."))


def on_language_update(
    request: LanguageIdRequest,
    response: LanguageIdResponse,
    start_times,
    detected_languages,
):
    # Update the detected languages if it has changed
    if (
        len(detected_languages[request.session_id]) == 0
        or response.detected_language != detected_languages[request.session_id][-1][1]
    ):
        detected_languages[request.session_id].append(
            (time.time() - start_times[request.session_id], response.detected_language)
        )


def evaluate_dataset(
    config,
    dataset,
    output_dir,
    first_n,
    num_workers,
    overwrite=False,
    no_simulate_realtime=False,
):
    logger = logging.getLogger("evaluation")
    output_path = output_dir / f"{dataset.name}.txt"
    partial_output_path = output_dir / f"{dataset.name}.partial.txt"
    language_id_path = output_dir / f"{dataset.name}_language_id.txt"

    if output_path.exists() and partial_output_path.exists() and not overwrite:
        logger.info(
            f"Predicted transcripts found at {output_path}, "
            + f"partial transcripts found at {partial_output_path}, "
            + "evaluating those"
        )
        transcripts = load_transcripts(output_path, first_n)
        partial_transcripts = load_partial(partial_output_path, first_n)
        detected_languages = load_detected_languages(language_id_path, first_n)
    else:
        logger.debug("Loading speech recognizer")
        partial_transcripts_container, transcript_prefixes = {}, {}
        detected_languages = {}
        start_times = {}
        transcript_listener = functools.partial(
            on_transcript,
            transcripts=partial_transcripts_container,
            prefixes=transcript_prefixes,
        )
        language_id_listener = functools.partial(
            on_language_update,
            detected_languages=detected_languages,
            start_times=start_times,
        )

        # Mock logger - no need to save audio files passed to recognizer
        mock_logger = mock.Mock()
        mock_logger.log_dir = output_dir / "logs"
        mock_logger.log_dir.mkdir(parents=True, exist_ok=True)

        def make_asr_service(language):
            service_config = copy.deepcopy(config)
            service_config.language = language
            return SpeechRecognitionService(
                config=service_config,
                logger=mock_logger,
                callback_fn=transcript_listener,
                language_id_callback_fn=language_id_listener,
            )

        logger.debug("Loaded speech recognizer")

        logger.info(f"Transcripts not found at {output_path}, computing predictions")
        transcripts, partial_transcripts = infer(
            make_asr_service,
            dataset,
            partial_transcripts_container,
            detected_languages,
            start_times,
            (output_path, partial_output_path, language_id_path),
            first_n,
            num_workers,
            no_simulate_realtime,
        )

    metrics = {}
    dataset_languages = [language for _, language, _ in dataset.utterances][:first_n]
    metrics["wer"], num_refs = score(dataset.references, transcripts, dataset_languages)

    if config.language == "zh":
        logger.info(f"CER score on {dataset.name}: {metrics['wer']:.1f}%")
    else:
        logger.info(f"WER score on {dataset.name}: {metrics['wer']:.1f}%")

    metrics["transcription_lag"] = score_latency(
        dataset.references,
        dataset.utterances,
        partial_transcripts,
    )
    logger.info(
        f"Transcription lag on {dataset.name}: {metrics['transcription_lag']:.2f}s"
    )

    reference_durations = {
        file_id: get_duration_seconds(wav_file)
        for file_id, _, wav_file in dataset.utterances
    }
    metrics["language_id_accuracy"] = score_language_id_accuracy(
        dataset.language, reference_durations, detected_languages
    )
    logger.info(
        f"Language ID accuracy on {dataset.name}: {metrics['language_id_accuracy']*100:.1f}%"
    )
    metrics["initial_asr_lag"] = score_initial_asr_lag(partial_transcripts)
    logger.info(f"Initial ASR lag on {dataset.name}: {metrics['initial_asr_lag']:.2f}s")

    return SpeechRecognitionEvaluationScore(**metrics), num_refs


def evaluate(
    name,
    config,
    dataset_dir,
    datasets,
    output_dir,
    first_n,
    num_workers,
    overwrite=False,
    save_wandb=True,
    no_simulate_realtime=False,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("evaluation")

    logger.info("Evaluating speech recognition")

    for dataset_name in datasets:
        test_set = SpeechRecognitionDataset(dataset_dir, dataset_name)
        dataset_score, num_refs = evaluate_dataset(
            config,
            test_set,
            output_dir,
            first_n,
            num_workers,
            overwrite=overwrite,
            no_simulate_realtime=no_simulate_realtime,
        )
        dataset_score.save(output_dir / f"{dataset_name}.json")

        if save_wandb:
            # Log evaluation results to W&B
            save_wandb_logs(
                config,
                test_set.to_dict(),
                num_refs,
                dataset_score,
                name=f"{name}-{dataset_name}",
                group="asr",
            )
