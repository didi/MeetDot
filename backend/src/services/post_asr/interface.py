from dataclasses import dataclass
from typing import Dict, List, Optional

from config import Config


@dataclass
class PostASRConfig(Config):
    remove_repetitions: bool = True


@dataclass
class PostASRRequest:
    transcript: str
    language: str


@dataclass
class PostASRResponse:
    transcript: str
