from dataclasses import dataclass, field
from typing import Optional

from config import Config


@dataclass
class LanguageIdConfig(Config):
    enabled: bool = True
    model_path: Optional[str] = "src/services/asr/language_id/models/best"
    confidence_threshold: float = 0.0
    num_consecutive_threshold: int = 8
    window_size_seconds: float = 6.0
    window_stride_seconds: float = 1.0
