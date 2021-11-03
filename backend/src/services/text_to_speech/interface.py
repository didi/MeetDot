from dataclasses import dataclass
from typing import Optional, Sequence, Union

from config import Config


@dataclass
class TTSConfig(Config):
    provider: str = "coqui-ai"
    language_type: str = "en-US"


@dataclass
class TTSRequest:
    session_id: str
    message_id: int  # calculated from the utterance_start_time
    text: str
    source_language: str
    target_language: str
    is_final: bool = True
    previous_translation: Optional[Union[Sequence[str], str]] = None

    def session_key(self):
        return (self.session_id, self.source_language, self.target_language)


@dataclass
class TTSResponse:
    audio_dir: str  # this is the audio's directory.
