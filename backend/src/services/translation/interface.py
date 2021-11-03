from dataclasses import dataclass
from typing import Optional, Sequence, Union

from config import Config


@dataclass
class TranslationConfig(Config):
    provider: str = "didi"
    bias_beta: Optional[float] = 0.2
    min_interval_ms: Optional[int] = 35
    min_interval_char: Optional[int] = 0
    custom_args: Optional[dict] = None


@dataclass
class TranslationRequest:
    session_id: str
    message_id: int  # calculated from the utterance_start_time
    text: str
    source_language: str
    target_language: str
    is_final: bool = True
    previous_translation: Optional[Union[Sequence[str], str]] = None
    is_chat: bool = False

    def session_key(self):
        return (self.session_id, self.source_language, self.target_language)


@dataclass
class TranslationResponse:
    translation: str
    raw_translation: Optional[Sequence[Sequence[str]]] = None
