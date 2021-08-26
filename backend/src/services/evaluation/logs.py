from typing import Dict

import wandb
from services.evaluation.score import EvaluationScore


def save_wandb_logs(
    model_config: Dict,
    test_set_config: Dict,
    num_refs: int,
    dataset_score: EvaluationScore,
    name: str,
    group: str,
):
    eval_config = {
        "model": model_config.to_dict(),
        "test_set": {
            **test_set_config,
            "eval_size": num_refs,
        },
    }

    run = wandb.init(
        config=eval_config, group=group, name=name, project="speech-translation"
    )

    for metric, value in dataset_score.__dict__.items():
        wandb.run.summary[metric] = value
    run.finish()
