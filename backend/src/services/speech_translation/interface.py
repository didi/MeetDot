from dataclasses import dataclass

from config import Config
from services.asr import SpeechRecognitionConfig, SpeechRecognitionResponse
from services.captioning import CaptioningConfig, CaptioningResponse
from services.translation import TranslationConfig, TranslationResponse
from services.post_translation import PostTranslationConfig, PostTranslationResponse


@dataclass
class SpeechTranslationConfig(Config):
    asr: SpeechRecognitionConfig = SpeechRecognitionConfig()
    translation: TranslationConfig = TranslationConfig()
    post_translation: PostTranslationConfig = PostTranslationConfig()
    captioning: CaptioningConfig = CaptioningConfig()


@dataclass
class SpeechTranslationRequest:
    session_id: str
    chunk: bytes
    end_utterance: bool = False
