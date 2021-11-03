import json
from copy import deepcopy

from config import Config
from services.speech_translation import SpeechTranslationConfig
from services.image_translation import ImageTranslationConfig


class RoomSettings(Config):
    """
    Settings used for the different components of the room
    """

    DEFAULT_CONFIG = {
        "st_services": SpeechTranslationConfig(),
        "img_services": ImageTranslationConfig(),
        "interface": {
            "audio": {"distortion": False},
            "games": {"word_guessing": False, "game_duration": "180", "max_skips": 3},
            "chatbot": {"enabled": False, "language": "en-US"},
            "summarizer": {
                "max_segments": 6,
                "segment_length_minutes": 10,
                "language": "en",
                "max_ngram_size": 3,
                "deduplication_threshold": 0.2,
                "num_of_keywords": 3,
            },
            "max_participants": 9,
            "captioning_active": True,
            "single_caption": True,
            "screen_sharing": True,
        },
        "save_audio_logs": False,
    }

    def __init__(self, settings=None):
        self.__dict__.update(
            deepcopy(RoomSettings.DEFAULT_CONFIG)
        )  # bind the dictionary to obj

        if settings is not None:
            self.deep_update(settings)

    def __repr__(self):
        return f"RoomSettings({repr(self.__dict__)})"
