import base64
import glob
import random
import string

import gevent
from locust import task
from locust.exception import StopUser

from .base import SpeechTranslationUser

LANGUAGE_CODES = ("en-US", "zh")
SILENCE_WAV_PATH = "wavs/silence.wav"
WAV_PATHS = {"en-US": glob.glob("wavs/en/*.wav"), "zh": glob.glob("wavs/zh/*.wav")}
letters = string.ascii_lowercase


class CreateRoomUser(SpeechTranslationUser):
    """
    User who creates a new meeting and enters it
    """

    MIN_TASKS = 5
    MAX_TASKS = 10

    def on_start(self):
        super().on_start()
        self.language = random.choice(LANGUAGE_CODES)
        self.room_id = "".join(random.choice(letters) for i in range(10))
        self.user_id = "".join(random.choice(letters) for i in range(10))
        self.client.post(
            "/rooms", json={"roomId": self.room_id, "settings": {}}, verify=False
        )
        self.socket.emit("on-page", f"room/{self.room_id}")
        self.socket.emit(
            "/join",
            {
                "name": "creator",
                "spokenLanguage": self.language,
                "captionLanguages": self.language,
                "userId": self.user_id,
                "roomId": self.room_id,
            },
        )

    def on_stop(self):
        """
        Leave the room and close the locust
        """
        self.socket.emit(
            "disconnect-user",
            {
                "userId": self.user_id,
            },
        )
        super().on_stop()

    @task
    def speak(self):
        """
        Load some speech from a .wav file and send it over the socket
        """
        wav_path = random.choice(WAV_PATHS[self.language])
        self.send_wav(wav_path, self.user_id, self.room_id)
        self.tasks_completed += 1

        if (
            self.tasks_completed >= CreateRoomUser.MIN_TASKS and random.random() > 0.2
        ) or self.tasks_completed >= CreateRoomUser.MAX_TASKS:
            raise StopUser

    @task
    def pause_speaking(self):
        """
        Send silence over the socket
        """
        self.send_wav(SILENCE_WAV_PATH, self.user_id, self.room_id)
        self.tasks_completed += 1

        if (
            self.tasks_completed >= CreateRoomUser.MIN_TASKS and random.random() > 0.2
        ) or self.tasks_completed >= CreateRoomUser.MAX_TASKS:
            raise StopUser
