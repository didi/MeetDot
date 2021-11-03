import functools
import logging
import time
from pathlib import Path
from typing import Dict, List, Tuple
from unittest import mock

import tqdm
from services.evaluation.logs import save_wandb_logs
from services.translation import (
    TranslationConfig,
    TranslationRequest,
    TranslationResponse,
    TranslationService,
)

from .score import TranslationEvaluationScore, score
from .test_set import TranslationDataset


def infer(
    config: TranslationConfig,
    sentences: List[str],
    source_language: str,
    target_language: str,
    output_paths: Tuple[Path, Path, Path],
    first_n: int,
):
    translations: Dict[str, str] = {}
    compute_times: Dict[str, float] = {}
    _on_translate = functools.partial(
        on_translate, translations=translations, compute_times=compute_times
    )
    translator = TranslationService(
        config, callback_fn=_on_translate, logger=mock.Mock()
    )
    (
        translation_output_source_path,
        translation_output_target_path,
        time_output_path,
    ) = output_paths
    translation_output_source_file = open(translation_output_source_path, "w")
    translation_output_target_file = open(translation_output_target_path, "w")
    time_output_file = open(time_output_path, "w")

    if first_n > 0:
        sentences = sentences[:first_n]

    for i, sentence in enumerate(tqdm.tqdm(sentences)):
        session_id = str(i)
        # Save start time
        compute_times[session_id] = time.time()
        translator(
            TranslationRequest(
                session_id=session_id,
                # message_id is calculated from the relative_time_offset. st
                # uses asr_response.relative_time_offset for this value. what
                # value to choose for mt?
                message_id=0,
                text=sentence,
                source_language=source_language,
                target_language=target_language,
            )
        )
        translator.end_session(session_id, wait_for_final=True)

        translation_output_source_file.write(f"{sentence}\n")
        translation_output_target_file.write(f"{translations[session_id]}\n")
        time_output_file.write(f"{compute_times[session_id]}\n")

    translation_output_source_file.close()
    translation_output_target_file.close()
    time_output_file.close()

    return [translations[str(i)] for i in range(len(translations))], [
        compute_times[str(i)] for i in range(len(compute_times))
    ]


def on_translate(
    request: TranslationRequest,
    response: TranslationResponse,
    translations: Dict[str, str],
    compute_times: Dict[str, float],
):
    translations[request.session_id] = response.translation
    compute_times[request.session_id] = time.time() - compute_times[request.session_id]


def load_predictions(output_path: Path, first_n: int = -1):
    predictions = []
    with open(output_path) as f:
        for line in f:
            predictions.append(line.strip())

            if first_n > 0 and len(predictions) >= first_n:
                break

    return predictions


def load_times(output_path: Path, first_n: int = -1):
    with open(output_path) as f:
        times = []

        for line in f:
            times.append(float(line.strip()))

            if first_n > 0 and len(times) >= first_n:
                break

    return times


def evaluate_dataset(config, dataset, output_dir, first_n, overwrite=False):
    logger = logging.getLogger("evaluation")
    output_source_path = output_dir / f"{dataset.name}.source.txt"
    output_target_path = output_dir / f"{dataset.name}.target.txt"
    output_ref_target_path = output_dir / f"{dataset.name}.target.ref.txt"
    time_output_path = output_dir / f"{dataset.name}_times.txt"

    if output_target_path.exists() and not overwrite:
        logger.info(f"Translations found at {output_target_path}, evaluating those")
        predictions = load_predictions(output_target_path, first_n=first_n)
        compute_times = load_times(time_output_path, first_n=first_n)

    else:
        logger.info(
            f"Translations not found at {output_target_path}, computing predictions"
        )
        predictions, compute_times = infer(
            config,
            dataset.source_sentences,
            dataset.source_language,
            dataset.target_language,
            (output_source_path, output_target_path, time_output_path),
            first_n,
        )
    # write ref target sentences to file
    with open(output_ref_target_path, "w") as f:
        f.write("\n".join(dataset.target_sentences))

    # Compute BLEU
    bleu, num_refs = score(
        dataset.target_sentences, predictions, dataset.target_language
    )
    logger.info(
        f"BLEU score on {dataset.name} for {dataset.source_language} -> "
        + f"{dataset.target_language}: {bleu.score}"
    )

    # Compute average compute time
    mean_compute_time = sum(compute_times) / len(dataset.target_sentences)
    logger.info(
        f"Average compute time (s) on {dataset.name} for {dataset.source_language}"
        + f" -> {dataset.target_language}: {mean_compute_time}"
    )

    return (
        TranslationEvaluationScore(
            bleu=bleu.score, mean_compute_time=mean_compute_time
        ),
        num_refs,
    )


def evaluate(
    name,
    config,
    dataset_dir,
    datasets,
    output_dir,
    first_n,
    overwrite=False,
    save_wandb=True,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("evaluation")

    logger.info(f"Evaluating translation on {datasets}")

    for dataset_name in datasets:
        test_set = TranslationDataset(dataset_dir, dataset_name)
        dataset_score, num_refs = evaluate_dataset(
            config, test_set, output_dir, first_n, overwrite=overwrite
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
                group="mt",
            )
