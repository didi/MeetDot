import argparse
import json
import logging
import os
import pprint
import sys
from pathlib import Path

from dotenv import load_dotenv

from services.evaluation.asr.evaluate import evaluate as evaluate_asr
from services.evaluation.asr.test_set import DATASETS as ASR_DATASETS
from services.evaluation.st.evaluate import evaluate as evaluate_st
from services.evaluation.st.test_set import DATASETS as ST_DATASETS
from services.evaluation.translation.evaluate import evaluate as evaluate_mt
from services.evaluation.translation.test_set import DATASETS as MT_DATASETS
from services.post_translation.interface import PostTranslationConfig
from services.speech_translation import SpeechTranslationConfig
from services.translation.interface import TranslationConfig

DEFAULT_DATASET_DIR = Path(__file__).parent / "data/"
if not os.path.isfile("../.env"):
    raise FileNotFoundError("could not find .env, run from backend directory")
load_dotenv(dotenv_path="../.env")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluation of ASR, MT, and speech translation systems. "
        + "Specify one or more of ASR, MT, or ST to run, "
        + "or evaluate all if unspecified."
    )
    parser.add_argument(
        "--dataset_dir",
        "-d",
        type=Path,
        default=DEFAULT_DATASET_DIR,
        help=f"Directory storing datasets, defaults to {DEFAULT_DATASET_DIR}",
    )
    parser.add_argument(
        "--asr", "-a", action="store_true", help="Run evaluation for ASR?"
    )
    parser.add_argument(
        "--asr-datasets", nargs="*", default=ASR_DATASETS, choices=ASR_DATASETS
    )
    parser.add_argument(
        "--mt", "-t", action="store_true", help="Run evaluation for MT?"
    )
    parser.add_argument(
        "--mt-datasets", nargs="*", default=MT_DATASETS, choices=MT_DATASETS
    )
    parser.add_argument(
        "--st", "-s", action="store_true", help="Run evaluation for speech translation?"
    )
    parser.add_argument(
        "--st-datasets",
        nargs="*",
        default=ST_DATASETS,
        help="Specify a speech-translation dataset.  If --only_predict is set, then you may also"
        "specify asr-datasets here, but must append a '-<language>' suffix to the asr dataset name"
        "to specify the target translation language of the asr-dataset, e.g. 'aishell-1-en'",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=Path(__file__).parent / "configs/default.json",
        help="Services configuration file",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="test",
        help="Name used to identify this evaluation run. Outputs will be saved to outputs/{name}",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Whether to overwrite existing files in output_dir",
    )
    parser.add_argument(
        "--first-n",
        type=int,
        default=-1,
        help="Specifies to only use the first N samples of the test set. "
        + "Ignored if output has already been computed, unless --overwrite is also specified.",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=1,
        help="Number of parallel workers to run",
    )
    parser.add_argument(
        "--no-simulate-realtime",
        action="store_true",
        default=False,
        help="Disable the feature which simulates the real scenario by "
        "inserting a short time interval between ASR requests.",
    )
    parser.add_argument(
        "--only-predict",
        action="store_true",
        default=False,
        help="Only generate predictions, don't run evaluation scorers. Currently only supported "
        "for speech translation evaluations. If set, you may specify asr-datasets for speech-"
        "translation, but you must append a '-<language>' suffix to the asr dataset name in order "
        "to specify the target translation language of the asr-dataset, e.g. 'aishell-1-en'",
    )
    parser.add_argument("--no-wandb", action="store_true")
    parser.add_argument("--verbose", action="store_true")

    return parser.parse_args()


if __name__ == "__main__":
    # Load command line args
    args = parse_args()

    # Initialize logger
    logger = logging.getLogger("evaluation")
    logger.setLevel(level=logging.DEBUG if args.verbose else logging.INFO)
    console = logging.StreamHandler()
    console.setLevel(level=logging.DEBUG if args.verbose else logging.INFO)
    logger.addHandler(console)

    # Set up output dir
    output_dir = Path(__file__).parent / "outputs" / args.name
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Outputs will be saved to/read from: %s" % output_dir)

    # Save config file or reload from output_dir
    config_path = output_dir / "config.json"
    if not os.path.isfile("../.env"):
        raise FileNotFoundError("could not find .env, run from backend directory")
    load_dotenv(dotenv_path="../.env")

    config = SpeechTranslationConfig()

    if (config_path.exists() and args.overwrite) or not config_path.exists():
        config.deep_update_with_json_config(args.config)
        with open(config_path, "w") as config_file:
            json.dump(config.to_dict(), config_file)
    else:
        config.deep_update_with_json_config(config_path)
        logger.info(
            f"Found existing config file at {config_path}, ignoring provided config "
            + "(use --overwrite to change this)"
        )
    logger.info(f"Running with {args.num_workers} parallel workers")
    logger.info("Evaluating using config:\n %s" % pprint.pformat(config.to_dict()))

    evaluate_all = not (args.asr or args.mt or args.st)

    if args.asr or evaluate_all:
        evaluate_asr(
            args.name,
            config.asr,
            args.dataset_dir,
            args.asr_datasets,
            output_dir / "asr",
            args.first_n,
            args.num_workers,
            overwrite=args.overwrite,
            save_wandb=not args.no_wandb,
            no_simulate_realtime=args.no_simulate_realtime,
        )

    if args.mt or evaluate_all:
        score = evaluate_mt(
            args.name,
            config.translation,
            args.dataset_dir,
            args.mt_datasets,
            output_dir / "translation",
            args.first_n,
            overwrite=args.overwrite,
            save_wandb=not args.no_wandb,
        )

    if args.st or evaluate_all:
        assert args.only_predict or len(
            set(ST_DATASETS).intersection(args.st_datasets)
        ) == len(args.st_datasets)
        score = evaluate_st(
            args.name,
            config,
            args.dataset_dir,
            args.st_datasets,
            output_dir / "st",
            args.first_n,
            args.num_workers,
            overwrite=args.overwrite,
            save_wandb=not args.no_wandb,
            no_simulate_realtime=args.no_simulate_realtime,
            only_predict=args.only_predict,
        )
