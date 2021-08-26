import collections
import glob
import json
import logging
import math
import string
import re
from pathlib import Path
from typing import List, Tuple, Optional

import services.evaluation.asr.test_set as asr_test_set
from utils import load_json, load_text_file

DATASETS = [
    "mslt-en-zh",
    "mslt-zh-en",
    "mslt-small-en-zh",
    "mslt-small-zh-en",
    "dwc1-zh-en",
    "dwc1-en-zh",
    "dwc1_16k-zh-en",
    "dwc1_16k-en-zh",
    "dwc1_longform_16k-zh-en",
    "dwc2-en-zh",
    "dwc2-zh-en",
    "dwc2_leading_silence_trimmed-en-zh",
    "dwc2_leading_silence_trimmed-zh-en",
]


class SpeechTranslationDataset:
    LANGUAGE_CODES = {
        "en": "en-US",
    }

    def __init__(self, dataset_dir: Path, dataset_name: str):
        self.logger = logging.getLogger("evaluation")
        self.source_language: str
        self.target_language: str
        self.wav_files: List[Tuple[str, str]]
        self.transcripts = List[str]
        self.translations = Optional[List[str]]
        # each element is the names mentioned in the transcript
        self.names = Optional[List[str]]
        # each element is the speaker of the transcript
        self.speakers = Optional[List[str]]
        self.dataset_dir = dataset_dir
        self.name = dataset_name
        asr_dataset = None
        for asr_name in asr_test_set.DATASETS:
            if dataset_name.startswith(asr_name):
                regex = re.match(f"^{asr_name}-([a-zA-Z]+)", dataset_name)
                assert (
                    regex
                ), f"When using an ASR dataset for speech-translation you must append a "
                "'-<target_language>' suffix to the dataset_name,  e.g. '{dataset_name}-en'"
                self.target_language = SpeechTranslationDataset.LANGUAGE_CODES.get(
                    regex.group(1), regex.group(1)
                )
                asr_dataset = asr_test_set.SpeechRecognitionDataset(
                    self.dataset_dir, asr_name
                )
                self.source_language = asr_dataset.language
                self.wav_files = [
                    (file_id, wav_path)
                    for file_id, _language, wav_path in asr_dataset.utterances
                ]
                self.transcripts = asr_dataset.references
                self.translations = None
                self.names = None
                self.speakers = None
                break

        if not asr_dataset:
            self.load_dataset(dataset_name)

            # Sort references and names by ID
            (
                self.wav_files,
                self.transcripts,
                self.translations,
                self.names,
                self.speakers,
            ) = map(
                list,
                zip(
                    *sorted(
                        zip(
                            self.wav_files,
                            self.transcripts,
                            self.translations,
                            self.names,
                            self.speakers,
                        ),
                        key=lambda x: x[0][0],
                    )
                ),
            )

    def load_dataset(self, dataset_name: str):
        if dataset_name.startswith("mslt") and dataset_name.count("-") == 2:
            self.load_mslt_dataset(dataset_name)
        elif dataset_name.startswith("dwc1") and dataset_name.count("-") == 2:
            self.load_dwc_dataset(dataset_name)
        elif dataset_name.startswith("dwc2") and dataset_name.count("-") == 2:
            self.load_dwc2_dataset(dataset_name)
        else:
            raise ValueError("Invalid dataset name: %s" % dataset_name)

    def get_utterance_id(self, filename: str):
        stem = Path(filename).stem

        return stem[: stem.find(".")]

    def read_snt_file(self, filename: str):
        with open(filename, "r", encoding="utf-16-le") as f:
            # Skip first two bytes, dataset includes some weird padding
            f.seek(2)

            # Read transcript
            transcript = f.read().strip().replace("\n", " ")

        return transcript

    def load_mslt_dataset(self, dataset_name: str):
        _, source_language, target_language = dataset_name.split("-")
        self.source_language = SpeechTranslationDataset.LANGUAGE_CODES.get(
            source_language, source_language
        )
        self.target_language = SpeechTranslationDataset.LANGUAGE_CODES.get(
            target_language, target_language
        )
        dataset_dir = (
            Path(self.dataset_dir) / f"st/{source_language}-{target_language}/mslt"
        )

        wav_files = glob.glob(str(dataset_dir / f"*.{source_language}.wav"))
        assert wav_files, "Couldn't find any wav_files in dataset_dir:%s" % dataset_dir
        source_snt_files = glob.glob(str(dataset_dir / f"*.T2.{source_language}.snt"))
        target_snt_files = glob.glob(str(dataset_dir / f"*.{target_language}.snt"))

        wav_files_by_id = {self.get_utterance_id(f): f for f in wav_files}
        source_files_by_id = {self.get_utterance_id(f): f for f in source_snt_files}
        target_files_by_id = {self.get_utterance_id(f): f for f in target_snt_files}

        self.wav_files, self.transcripts, self.translations = [], [], []

        for file_id, wav_file in sorted(wav_files_by_id.items()):
            assert file_id in source_files_by_id and file_id in target_files_by_id, (
                "Couldn't find source and target files for file_id:%s" % file_id
            )
            self.wav_files.append((file_id, wav_file))
            self.transcripts.append(self.read_snt_file(source_files_by_id[file_id]))
            self.translations.append(self.read_snt_file(target_files_by_id[file_id]))

        self.logger.info(f"Loaded {len(self.transcripts)} utterances from MSLT")

    def load_dwc_dataset(self, dataset_name: str):
        dataset_basename, source_language, target_language = dataset_name.split("-")
        self.source_language = SpeechTranslationDataset.LANGUAGE_CODES.get(
            source_language, source_language
        )
        self.target_language = SpeechTranslationDataset.LANGUAGE_CODES.get(
            target_language, target_language
        )
        dataset_dir = (
            Path(self.dataset_dir)
            / f"st/{source_language}-{target_language}/{dataset_basename}"
        )
        wav_files = glob.glob(str(dataset_dir / "*.wav"))
        transcript_filepath = str(dataset_dir / "transcript.json")
        translation_filepath = str(dataset_dir / "translation.txt")

        wav_files_by_id = {Path(f).stem: f for f in wav_files}
        wav_files_sortedby_id = collections.OrderedDict(sorted(wav_files_by_id.items()))
        transcripts_json = load_json(transcript_filepath)
        transcripts = [
            fragment["lines"][0] for fragment in transcripts_json["fragments"]
        ]
        translations = load_text_file(translation_filepath)

        self.wav_files, self.transcripts, self.translations = [], [], []

        for file_id, wav_file in wav_files_sortedby_id.items():
            self.wav_files.append((file_id, wav_file))
        self.transcripts = transcripts
        self.translations = translations

        self.logger.info(f"Loaded {len(self.transcripts)} utterances from dwc")

    def load_dwc2_dataset(self, dataset_name: str):
        dataset_basename, source_language, target_language = dataset_name.split("-")
        self.source_language = SpeechTranslationDataset.LANGUAGE_CODES.get(
            source_language, source_language
        )
        self.target_language = SpeechTranslationDataset.LANGUAGE_CODES.get(
            target_language, target_language
        )
        dataset_dir = (
            Path(self.dataset_dir)
            / f"st/{source_language}-{target_language}/{dataset_basename}"
        )
        (
            self.wav_files,
            self.transcripts,
            self.translations,
            self.names,
            self.speakers,
        ) = ([], [], [], [], [])
        meetings_dirs = glob.glob(str(dataset_dir / "*_meeting"))

        for meeting_dir in meetings_dirs:
            meeting_dir = Path(meeting_dir)
            meeting_date_str = Path(meeting_dir).stem.split("_")[
                0
            ]  # 03-26_meeting -> 03-26
            wav_files = glob.glob(str(meeting_dir / "*.wav"))
            transcript_filepath = str(meeting_dir / "transcript.txt")
            translation_filepath = str(meeting_dir / "translation.txt")
            name_filepath = str(meeting_dir / "names.participants.txt")
            speaker_filepath = str(meeting_dir / "speakers.txt")

            wav_files_by_id = {
                "_".join([meeting_date_str, Path(f).stem]): f for f in wav_files
            }
            wav_files_sortedby_id = collections.OrderedDict(
                sorted(wav_files_by_id.items())
            )
            transcripts = load_text_file(transcript_filepath)
            translations = load_text_file(translation_filepath)
            # read name file
            if Path(name_filepath).exists():
                names = [
                    [n.strip() for n in line.lower().split("\t") if n.strip()]
                    for line in load_text_file(name_filepath)
                ]
            else:
                names = [[]] * len(transcripts)
            # read speaker file
            if Path(speaker_filepath).exists():
                speakers = []
                current_speaker = None
                with open(speaker_filepath) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            current_speaker = line
                        speakers.append(current_speaker)
            else:
                speakers = [""] * len(transcripts)

            for file_id, wav_file in wav_files_sortedby_id.items():
                self.wav_files.append((file_id, wav_file))
            self.transcripts += transcripts
            self.translations += translations
            self.names += names
            self.speakers += speakers
        self.logger.info(f"Loaded {len(self.transcripts)} utterances from dwc2")

    def to_dict(self):
        return {
            "name": self.name,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "size": len(self.transcripts),
        }
