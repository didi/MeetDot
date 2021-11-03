from dataclasses import dataclass, field
from typing import Dict, List, Union

from config import Config


@dataclass
class CaptioningConfig(Config):
    strategy: str = "linewise_scroll"
    num_lines: int = 3
    characters_per_line: int = 60
    enable_highlight: bool = True
    punctuation_sensitive: bool = True


@dataclass
class CaptioningRequest:
    session_id: str
    message_id: int
    original_language: str
    target_language: str
    utterance: str
    utterance_complete: bool


@dataclass
class CaptioningResponse:
    lines: List[str]
    line_index: int
    highlight_boundaries: Union[List[int], None] = None
