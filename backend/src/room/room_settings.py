import json
from copy import deepcopy

from config import Config
from services.speech_translation import SpeechTranslationConfig


class RoomSettings(Config):
    """
    Settings used for the different components of the room
    """

    DEFAULT_CONFIG = {
        "services": SpeechTranslationConfig(),
        "interface": {
            "audio": {"distortion": False},
            "games": {"word_guessing": False, "game_duration": "180", "max_skips": 3},
            "chatbot": {"enabled": False, "language": "en-US"},
            "max_participants": 9,
            "captioning_active": True,
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
