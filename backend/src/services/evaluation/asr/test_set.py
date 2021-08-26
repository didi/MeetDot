import datetime
import glob
import logging
from pathlib import Path
import re
from typing import List, Tuple

from .language_id import parse_language_id_block

from utils import load_text_file

DATASETS = [
    "librispeech",
    "aishell-1",
    "aishell-4",
    "language-id",
    "keywords",
    "multi-TED_es",
    "multi-TED_pt",
]


class SpeechRecognitionDataset:
    def __init__(self, dataset_dir, dataset_name):
        self.logger = logging.getLogger("evaluation")
        self.language: str
        self.references: List[str]
        self.utterances: List[Tuple[str, str, str]]
        self.dataset_dir = dataset_dir
        self.load_dataset(dataset_name)
        self.name = dataset_name

    def load_dataset(self, dataset_name):
        if dataset_name == "librispeech":
            self.load_librispeech()
        elif dataset_name == "aishell-1":
            self.load_aishell1()
        elif dataset_name == "aishell-4":
            self.load_aishell4()
        elif dataset_name == "language-id":
            self.load_language_id()
        elif dataset_name == "keywords":
            self.load_keywords()
        elif dataset_name.startswith("multi-TED"):
            lang_code = dataset_name.split("_")[-1]
            self.load_multi_ted(language_code=lang_code)
        else:
            raise ValueError("Could not load dataset: %s" % dataset_name)

        # Sort references by ID
        self.utterances, self.references = map(
            list,
            zip(*sorted(zip(self.utterances, self.references), key=lambda x: x[0][0])),
        )

    def load_librispeech(self):
        self.language = "en-US"

        dataset_dir = Path(self.dataset_dir) / "asr/en/librispeech/test-clean"

        if not dataset_dir.exists():
            raise ValueError(f"Dataset not found at {dataset_dir}")

        chapters = glob.glob(str(dataset_dir / "*" / "*"))
        self.utterances = []
        self.references = []

        for chapter in chapters:
            wav_files_by_id = {Path(f).stem: f for f in glob.glob(chapter + "/*.wav")}
            transcript_file = glob.glob(chapter + "/*.trans.txt")[0]
            with open(transcript_file) as f:
                for line in f:
                    line = line.strip()
                    file_id, *transcript = line.split(" ")
                    transcript = " ".join(transcript)

                    if file_id not in wav_files_by_id:
                        continue
                    else:
                        self.utterances.append(
                            (file_id, self.language, wav_files_by_id[file_id])
                        )
                        self.references.append(transcript)

        self.logger.info(f"Loaded {len(self.references)} utterances from librispeech")

    def load_aishell1(self):
        self.language = "zh"

        dataset_dir = Path(self.dataset_dir) / "asr/zh/aishell"

        speakers = sorted(glob.glob(str(dataset_dir / "wav/*")))
        transcript_filename = dataset_dir / "transcripts.txt"
        self.utterances = []
        self.references = []

        wav_files_by_id = {}

        for speaker in speakers:
            files = sorted(glob.glob(str(Path(speaker) / "*.wav")))
            wav_files_by_id.update({Path(f).stem: f for f in files})

        with open(transcript_filename) as transcript_file:
            for line in transcript_file:
                line = line.strip()
                file_id, *transcript = line.split(" ")
                transcript = " ".join(transcript).strip()

                if file_id not in wav_files_by_id:
                    continue
                else:
                    self.utterances.append(
                        (file_id, self.language, wav_files_by_id[file_id])
                    )
                    self.references.append(transcript)

        self.logger.info(f"Loaded {len(self.references)} utterances from AISHELL-1")

    def load_aishell4(self):
        self.language = "zh"

        dataset_dir = Path(self.dataset_dir) / "asr/zh/aishell-4"

        transcript_filename = dataset_dir / "transcripts.txt"
        self.utterances = []
        self.references = []

        wav_files_by_id = {}

        files = sorted(dataset_dir.glob("wav_1ch/*.wav"))
        wav_files_by_id.update({f.stem: str(f) for f in files})

        with open(transcript_filename) as transcript_file:
            for line in transcript_file:
                line = line.strip()
                file_id, *transcript = line.split(": ")
                transcript = " ".join(transcript).strip()
                # Remove content in angle brackets: <>
                transcript = re.sub(r"<.*?>", "", transcript)

                if file_id not in wav_files_by_id:
                    continue
                else:
                    self.utterances.append(
                        (file_id, self.language, wav_files_by_id[file_id])
                    )
                    self.references.append(transcript)

        self.logger.info(f"Loaded {len(self.references)} utterances from AISHELL-4")

    def load_language_id(self):

        dataset_dir = Path(self.dataset_dir) / "asr/language-id"

        wav_files = sorted(glob.glob(str(dataset_dir / "*.wav")))
        wav_files_by_id = {Path(f).stem: f for f in wav_files}
        language_id_filename = dataset_dir / "language_ids.txt"

        self.utterances = []
        self.references = []
        self.language = {}

        # Parse language ID files
        with open(language_id_filename) as language_id_file:
            block = []
            for line in language_id_file:
                line = line.strip()
                if line == "":
                    # Parse block
                    file_id, intervals = parse_language_id_block(block)
                    if file_id in wav_files_by_id:
                        self.utterances.append(
                            (file_id, intervals[0][1], wav_files_by_id[file_id])
                        )
                        self.references.append("")
                        self.language[file_id] = intervals
                    block = []
                else:
                    block.append(line)
            file_id, intervals = parse_language_id_block(block)
            self.utterances.append((file_id, intervals[0][1], wav_files_by_id[file_id]))
            self.references.append("")
            self.language[file_id] = intervals

        self.logger.info(
            f"Loaded {len(self.references)} utterances from language-id test set"
        )

    def load_keywords(self):
        self.language = "en-US"
        self.utterances = []
        self.references = []
        self.keywords = []
        dataset_dir = Path(self.dataset_dir) / "asr/en/keywords"

        # Load wav files by utterance ID
        wav_files_by_id = {}
        wav_files = sorted(glob.glob(str(dataset_dir / "wavs" / "*.wav")))

        for wav_file in wav_files:
            wav_files_by_id[Path(wav_file).stem] = wav_file

        transcript_filename = dataset_dir / "transcripts.txt"
        keywords_filename = dataset_dir / "keywords.txt"

        with open(transcript_filename) as transcript_file, open(
            keywords_filename
        ) as keywords_file:

            for transcript_line, keywords_line in zip(transcript_file, keywords_file):
                file_id, *transcript = transcript_line.strip().split(" ")
                transcript = " ".join(transcript).strip()
                keywords = keywords_line.strip().upper().split(",")

                if file_id not in wav_files_by_id:
                    self.logger.warning(f"Could not load file {file_id}")

                    continue
                else:
                    self.utterances.append((file_id, "en-US", wav_files_by_id[file_id]))
                    self.references.append(transcript)
                    self.keywords.append({k: keywords.count(k) for k in keywords})

        self.logger.info(f"Loaded {len(self.references)} utterances from keywords")

    def load_multi_ted(self, language_code):
        if language_code == "es":
            self.language = "es-ES"
        if language_code == "pt":
            self.language = "pt-BR"
        dataset_dir = Path(self.dataset_dir) / f"asr/{language_code}/multi_TED"

        if not dataset_dir.exists():
            self.logger.error(f"Cannot find multi_TED {language_code} dataset dir.")
            raise ValueError(f"Could not load dataset multi_TED {language_code}.")
        audio_segments_dir = dataset_dir / "audio_segments/"
        segments_filename = dataset_dir / f"txt/segments"
        transcript_filename = dataset_dir / f"txt/test.{language_code}"

        segments = load_text_file(str(segments_filename))

        if not audio_segments_dir.exists():
            # first loading multi_TED test set, audio segments are not existed
            self.logger.error(f"Cannot find audio_segments sub dir.")
            raise ValueError(
                f"Could not load dataset multi_TED {language_code} successfully."
            )
        # load wav files and reference transcripts
        self.references = load_text_file(transcript_filename)
        self.utterances = [
            (
                "f{0:0=6d}".format(idx + 1),
                self.language,
                str(audio_segments_dir / "f{0:0=6d}.wav".format(idx + 1)),
            )
            for idx in range(len(segments))
        ]

    def to_dict(self):
        return {
            "name": self.name,
            "language": self.language,
            "size": len(self.references),
        }
