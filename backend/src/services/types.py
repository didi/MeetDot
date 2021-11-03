from typing import Union

from services.asr import SpeechRecognitionRequest, SpeechRecognitionResponse
from services.captioning import CaptioningRequest, CaptioningResponse
from services.post_translation import PostTranslationRequest, PostTranslationResponse
from services.translation import TranslationRequest, TranslationResponse

ServiceRequest = Union[
    SpeechRecognitionRequest,
    TranslationRequest,
    PostTranslationRequest,
    CaptioningRequest,
]

ServiceResponse = Union[
    SpeechRecognitionResponse,
    TranslationResponse,
    PostTranslationResponse,
    CaptioningResponse,
]
