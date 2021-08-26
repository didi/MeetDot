import logging
from dataclasses import dataclass

import sacrebleu
from services.evaluation.score import EvaluationScore


@dataclass
class TranslationEvaluationScore(EvaluationScore):
    bleu: float
    mean_compute_time: float


def score(references, predictions, target_language="en-US"):
    logger = logging.getLogger("evaluation")

    min_len = min(len(predictions), len(references))

    if len(predictions) != len(references):
        logger.warning(
            f"Found {len(references)} references, {len(predictions)} translations. "
            + f"Evaluating only the first {min_len}."
        )
    predictions = predictions[:min_len]
    references = references[:min_len]
    assert (
        target_language != "ja"
    ), "Japanese tokenizer not supported, add sacrebleu[ja] to requirements.txt first"
    tokenizer = "zh" if target_language == "zh" else "13a"
    bleu = sacrebleu.corpus_bleu(predictions, [references], tokenize=tokenizer)
    num_refs = len(references)

    return bleu, num_refs
