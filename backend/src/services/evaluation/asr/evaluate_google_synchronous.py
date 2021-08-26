import argparse
import logging
from pathlib import Path

import tqdm
from google.cloud import speech

from evaluate import load_predictions, score
from test_set import SpeechRecognitionDataset

ASR_TEST_SETS = {"en-US": "librispeech", "zh": "aishell-1"}


def infer(test_set, language, output_filename):
    predictions = []
    client = speech.SpeechClient()
    output_file = open(output_filename, "w")

    for wav_filename in tqdm.tqdm(test_set.wav_files):
        with open(wav_filename, "rb") as audio_file:
            content = audio_file.read()

        audio = speech.types.RecognitionAudio(content=content)
        config = speech.types.RecognitionConfig(
            encoding=speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=language,
        )

        response = client.recognize(config=config, audio=audio)

        if len(response.results) == 0:
            prediction = "<TIMEOUT>"
        else:
            prediction = response.results[0].alternatives[0].transcript
        predictions.append(prediction)
        utterance_id = Path(wav_filename).stem
        output_file.write(f"{utterance_id} {prediction}\n")

    output_file.close()

    return predictions


def evaluate(language, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("evaluation")

    logger.info("Evaluating Google synchronous speech recognition")

    test_set = ASR_TEST_SETS[language]
    dataset = SpeechRecognitionDataset(test_set)
    output_filename = output_dir / f"{test_set}.txt"

    if output_filename.exists():
        logger.info(
            f"Predicted transcripts found at {output_filename}, evaluating those"
        )
        predictions = load_predictions(output_filename)
    else:
        logger.info(
            f"Predicted transcripts not found at {output_filename}, computing them"
        )
        predictions = infer(dataset, language, output_filename)

    wer = score(
        dataset.references,
        predictions,
        language=language,
    )

    if language == "zh":
        logger.info(f"CER score on {test_set}: {100*wer:.1f}%")
    else:
        logger.info(f"WER score on {test_set}: {100*wer:.1f}%")

    return wer


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluation of Google synchronous ASR")
    parser.add_argument("--language", type=str, default="en-US")
    parser.add_argument(
        "--output_dir",
        "-o",
        type=Path,
        default="outputs/google_sync",
        help="Path to save or load test set predictions",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    # Initialize logger
    logger = logging.getLogger("evaluation")
    logger.setLevel(level=logging.DEBUG if args.verbose else logging.INFO)
    console = logging.StreamHandler()
    console.setLevel(level=logging.DEBUG if args.verbose else logging.INFO)
    logger.addHandler(console)

    output_dir = Path(__file__).parent.parent / args.output_dir
    logger.info("Outputs will be saved to/read from: %s" % output_dir)

    evaluate(args.language, output_dir)
