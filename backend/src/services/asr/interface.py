from dataclasses import dataclass, field
import time
from typing import Optional

from config import Config
from .language_id.language_id_config import LanguageIdConfig


@dataclass
class SpeechRecognitionConfig(Config):
    providers: dict = field(
        default_factory=lambda: {
            "en-US": "wenet",
            "zh": "wenet",
            "es-ES": "google",
            "pt-BR": "google",
        }
    )
    field(default_factory=lambda: [])
    sample_rate_hertz: int = 16000
    chunk_size: int = 1600
    stability_threshold: float = 0.5
    language: str = ""  # language is set either in start_listening or middleware
    encoding: Optional[str] = None
    language_id: LanguageIdConfig = LanguageIdConfig()
    middleware_provider: Optional[str] = None

    def __post_init__(self):
        # Error checking
        if self.middleware_provider is not None and len(self.providers) < 2:
            raise ValueError(
                "At least two languages must be specified to run middleware"
            )
            # Otherwise, you don't need the middleware

        if self.language_id.enabled and self.middleware_provider is not None:
            raise ValueError(
                "Middleware is currently not compatible with other language id"
            )


@dataclass
class SpeechRecognitionRequest:
    session_id: str
    chunk: bytes = field(repr=False)
    end_utterance: bool = False


@dataclass
class SpeechRecognitionResponse:
    transcript: str
    # offset from the beginning of the recording in s. this becomes the primary key later
    utterance_start_time: float

    # length of utterance in seconds
    utterance_length: float
    is_final: bool
    # Predicted language ID
    language: str = ""


@dataclass
class LanguageIdRequest:
    session_id: str


@dataclass
class LanguageIdResponse:
    detected_language: str
