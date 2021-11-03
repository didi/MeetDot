import threading
from dataclasses import dataclass

from services.asr import SpeechRecognitionService


@dataclass
class Session:
    session_id: str
    language: str
    asr_service: SpeechRecognitionService
    recognizer_thread: threading.Thread
    language_id_thread: threading.Thread
