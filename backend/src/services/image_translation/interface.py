from dataclasses import dataclass
from typing import List, Optional

from PIL.PngImagePlugin import PngImageFile

from config import Config
from ..translation import TranslationConfig


@dataclass
class ImageTranslationConfig(Config):
    # TODO LS: Optional, if you have a lot of config for OCR, factor it into an OcrConfig
    # if it's just the provider, this is fine though
    ocr_provider: str = "fake"
    mt: TranslationConfig = TranslationConfig()


@dataclass
class ImageTranslationRequest:
    session_id: str
    source_language: str
    target_language: str
    source_image: PngImageFile  # or another format, up to you


@dataclass
class ImageTranslationResponse:
    text: str
    result_image: PngImageFile


@dataclass
class OcrRequest:
    # source_language may support Optional[str], in which case the
    # OcrResponse should include a source_language as output
    source_language: str
    target_language: str
    source_image: PngImageFile


@dataclass
class OcrResponse:
    text: str


@dataclass
class SubstitutionRequest:
    text: str
    source_image: PngImageFile


@dataclass
class SubstitutionResponse:
    text: str  # For debugging and tooltips only
    result_image: PngImageFile
