from pathlib import Path
import functools
import json
from unittest import mock
import time
import wave
import yaml
import tqdm

from services.asr import (
    SpeechRecognitionConfig,
    SpeechRecognitionRequest,
    SpeechRecognitionResponse,
    SpeechRecognitionService,
)
from utils import start_thread


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
    transcripts[request.session_id].append(delimiter.join(utterances))

    if response.is_final:
        prefixes[request.session_id].append(response.transcript.rstrip("."))


def get_clip(wav_file, start_time, duration):
    start_frame = int(start_time * wav_file.getframerate())
    chunk_size = 1600
    wav_file.setpos(start_frame)
    i = 0
    while i < duration:
        chunk = wav_file.readframes(chunk_size)
        i += chunk_size / wav_file.getframerate()
        yield chunk


def read_lines(manifest_file):
    with open(manifest_file) as f:
        for line in f:
            yield yaml.load(line, Loader=yaml.FullLoader)[0]


def main(wav_dir, manifest_file, output_file):
    config = SpeechRecognitionConfig()
    config.language = "en-US"
    partial_transcripts, transcript_prefixes = {}, {}
    transcript_listener = functools.partial(
        on_transcript,
        transcripts=partial_transcripts,
        prefixes=transcript_prefixes,
        language=config.language,
    )
    make_recognizer = lambda: SpeechRecognitionService(
        config=config,
        # Mock logger - no need to save audio files passed to recognizer
        logger=mock.Mock(),
        callback_fn=transcript_listener,
    )

    open(output_file, "w").close()

    lines = read_lines(manifest_file)

    open_wav_file = None
    transcripts = {}
    speaker_id = None
    i = 0
    for line in tqdm.tqdm(lines, total=184801):
        recognizer = make_recognizer()
        thread = start_thread(recognizer.run)
        if line["wav"] != open_wav_file:
            if open_wav_file is not None:
                open_wav_file.close()
            open_wav_file = wave.open(str(wav_dir / line["wav"]))
        if line["speaker_id"] != speaker_id:
            speaker_id = line["speaker_id"]
            i = 0
        else:
            i += 1
        utterance_id = f"{line['speaker_id']}_{i}"
        partial_transcripts[utterance_id] = []
        for chunk in get_clip(open_wav_file, line["offset"], line["duration"]):
            recognizer(SpeechRecognitionRequest(session_id=utterance_id, chunk=chunk))

        # Clean up recognizer
        recognizer.end_utterance()
        recognizer.wait_for_final()
        thread.join(timeout=10)

        # Collect and save the final transcripts
        utterance_transcripts = partial_transcripts[utterance_id]
        transcripts[utterance_id] = (
            utterance_transcripts[-1] if len(utterance_transcripts) else ""
        )

        with open(output_file, "a") as f:
            f.write(f"{utterance_id}: {transcripts[utterance_id]}\n")


if __name__ == "__main__":
    partition = "train"
    dataset_dir = Path("/home/shared/datasets/mustc-en-zh/data") / partition
    manifest_file = dataset_dir / f"txt/{partition}.yaml"
    output_file = Path("/home/ark/tmp/mustc_outputs.txt")
    main(dataset_dir / "wav", manifest_file, output_file)
