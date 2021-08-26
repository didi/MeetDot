from dataclasses import dataclass
from typing import Optional

from config import Config
from .language_id.config import LanguageIdConfig


@dataclass
class SpeechRecognitionConfig(Config):
    provider: str = "wenet"
    sample_rate_hertz: int = 16000
    chunk_size: int = 1600
    stability_threshold: float = 0.5
    language: str = ""
    encoding: Optional[str] = None
    language_id: LanguageIdConfig = LanguageIdConfig()


@dataclass
class SpeechRecognitionRequest:
    session_id: str
    chunk: bytes
    end_utterance: bool = False


@dataclass
class SpeechRecognitionResponse:
    transcript: str
    # offset from the beginning of the recording in ms. this becomes the primary key later
    relative_time_offset: int
    is_final: bool
    # Predicted language ID
    language: str = ""


@dataclass
class LanguageIdRequest:
    session_id: str


@dataclass
class LanguageIdResponse:
    detected_language: str
