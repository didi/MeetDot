from collections import defaultdict
from dataclasses import dataclass


@dataclass
class Utterance:
    speaker_id: str
    message_id: int
    speaker_name: str
    speaker_language: str
    text: str
    timestamp: float


class TranscriptList:
    """Holds transcripts"""

    def __init__(self):
        self.transcripts = defaultdict(list)

    def get(self, lang: str):
        """
        Get the existing transcript in a given language.
        If the first speaker of a language joined the room partway through,
        the transcript will only start from when they joined.
        """
        return self.transcripts.get(lang, [])

    def put(self, lang: str, utterance: Utterance):
        self.transcripts[lang].append(utterance)

    def export(self, lang: str):
        """Export a transcript to file"""
        raise NotImplementedError
