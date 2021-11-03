from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class CompletedUtterance:
    message_id: int
    speaker_name: str
    utterance: str
    language: str
    translations: List[Tuple[str, str]]
