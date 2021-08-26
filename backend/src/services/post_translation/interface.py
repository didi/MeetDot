from dataclasses import dataclass, field
from typing import Dict, List, Optional

from config import Config


@dataclass
class PostTranslationConfig(Config):
    # TODO: support changing params after initialization
    mask_k: int = 4
    disable_masking_before_k: bool = False
    translate_k: int = 0
    remove_profanity: bool = True
    add_punctuation: bool = True


@dataclass
class PostTranslationRequest:
    session_id: str
    message_id: int
    translation: str
    is_final: bool
    original_language: str
    language: str


@dataclass
class PostTranslationResponse:
    translation: str
