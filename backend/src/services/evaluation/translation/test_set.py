import logging
import re
import glob
from pathlib import Path
from typing import List

from bs4 import BeautifulSoup

from utils import load_text_file


DATASETS = [
    "iwslt-2010-en-zh",
    "iwslt-2011-en-zh",
    "iwslt-2012-en-zh",
    "iwslt-2013-en-zh",
    "iwslt-2014-en-zh",
    "iwslt-2015-en-zh",
    "iwslt-2010-zh-en",
    "iwslt-2011-zh-en",
    "iwslt-2012-zh-en",
    "iwslt-2013-zh-en",
    "iwslt-2014-zh-en",
    "iwslt-2015-zh-en",
    "dwc2-en-zh",
    "dwc2-zh-en",
]


class TranslationDataset:
    LANGUAGE_CODES = {"en": "en-US", "zh": "zh"}

    def __init__(self, dataset_dir, dataset_name):
        self.logger = logging.getLogger("evaluation")

        self.source_language: str
        self.target_language: str
        self.source_sentences: List[str]
        self.target_sentences: List[str]
        self.dataset_dir = dataset_dir
        self.load_dataset(dataset_name)
        self.name = dataset_name

    def load_dataset(self, dataset_name):
        if dataset_name.startswith("dwc2") and dataset_name.count("-") == 2:
            self.load_dwc2_dataset(dataset_name)
        else:
            self.load_iwslt_dataset(dataset_name)

    def load_iwslt_dataset(self, dataset_name):
        # Try to match IWSLT dataset pattern
        iwslt_matches = re.match("iwslt-(201[0-5])-(en|zh)-(zh|en)", dataset_name)

        if iwslt_matches is not None:
            year, source_language, target_language = iwslt_matches.groups()
            dataset_dir = Path(self.dataset_dir) / "mt/en-zh/TED" / year
            source_dataset_file = (
                dataset_dir / f"IWSLT17.TED.tst{year}.zh-en.{source_language}.xml"
            )
            target_dataset_file = (
                dataset_dir / f"IWSLT17.TED.tst{year}.zh-en.{target_language}.xml"
            )

            self.source_language = TranslationDataset.LANGUAGE_CODES[source_language]
            self.target_language = TranslationDataset.LANGUAGE_CODES[target_language]
            self.source_sentences = self.load_xml_dataset(source_dataset_file)
            self.target_sentences = self.load_xml_dataset(target_dataset_file)
        else:
            self.logger.error(f"Could not load dataset {dataset_name}")
            raise ValueError(f"Could not load dataset {dataset_name}")

    def load_xml_dataset(self, filename: Path) -> List[str]:
        """
        Load sentences from IWSLT xml file format
        """
        self.logger.debug(f"Loading XML dataset from {filename}")
        with open(filename) as f:
            soup = BeautifulSoup(f.read(), features="lxml")
            sentences = [s.text.strip() for s in soup.find_all("seg")]
        self.logger.debug(
            f"Finished loading {len(sentences)} sentences from {filename}"
        )

        return sentences

    def load_dwc2_dataset(self, dataset_name):
        # Try to match DWC2 dataset pattern
        dwc2_matches = re.match("dwc2-(en|zh)-(zh|en)", dataset_name)
        source_language, target_language = dwc2_matches.groups()
        self.source_language = TranslationDataset.LANGUAGE_CODES[source_language]
        self.target_language = TranslationDataset.LANGUAGE_CODES[target_language]

        dataset_dir = (
            Path(__file__).parent.parent
            / f"data/st/{source_language}-{target_language}/dwc2"
        )
        self.source_sentences, self.target_sentences, wav_file_ids = [], [], []
        meetings_dirs = glob.glob(str(dataset_dir / "*_meeting"))

        for meeting_dir in meetings_dirs:
            meeting_dir = Path(meeting_dir)
            transcript_filepath = str(meeting_dir / "transcript.txt")
            translation_filepath = str(meeting_dir / "translation.txt")

            transcripts = load_text_file(transcript_filepath)
            translations = load_text_file(translation_filepath)

            self.source_sentences += transcripts
            self.target_sentences += translations
            wav_files = glob.glob(str(meeting_dir / "*.wav"))
            meeting_date_str = Path(meeting_dir).stem.split("_")[
                0
            ]  # 03-26_meeting -> 03-26
            wav_file_ids += sorted(
                ["_".join([meeting_date_str, Path(f).stem]) for f in wav_files]
            )

        self.logger.info(f"Loaded {len(self.source_sentences)} utterances from dwc2")

        # Sort references by ID
        wav_file_ids, self.source_sentences, self.target_sentences = map(
            list,
            zip(
                *sorted(
                    zip(wav_file_ids, self.source_sentences, self.target_sentences),
                    key=lambda x: x[0],
                )
            ),
        )

    def to_dict(self):
        """
        Dictionary representation of test set
        """

        return {
            "name": self.name,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "size": len(self.source_sentences),
        }
