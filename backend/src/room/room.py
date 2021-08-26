from enum import Enum
import logging
import os

import requests

from logger import Logger
from services.manager import Manager
from .room_settings import RoomSettings


class RoomType(str, Enum):
    MEETING = "meeting"
    LIVE = "live"  # Daily.co video calling not required


class RoomNotCreated(Exception):
    pass


class Room:
    def __init__(self, room_id, room_type, log_dir, socket, settings={}):
        self.room_id = room_id
        self.room_type = room_type
        self.has_had_participants = False
        self.participants = {}
        self.settings = RoomSettings(settings)
        self.is_captioning_active = self.settings.interface["captioning_active"]
        self.logger = Logger(
            log_dir / room_id,
            get_participant_name=self.participant_name,
            room_config=self.settings,
            log_level=logging.DEBUG,
        )

        if room_type == RoomType.MEETING:
            self.daily_url = self.get_daily_url()

        if self.is_captioning_active:
            self.manager = Manager(room=self, socket=socket)

    def get_daily_url(self):
        # Create a room in Daily.co with the REST API
        DAILY_ENDPOINT = os.getenv("DAILY_API_BASE_URL") + "/rooms"
        DAILY_AUTH_KEY = os.getenv("DAILY_API_AUTH_KEY")

        room_response = requests.post(
            url=DAILY_ENDPOINT,
            json={"name": self.room_id, "privacy": "public"},
            headers={"Authorization": f"Bearer {DAILY_AUTH_KEY}"},
        )
        if room_response.status_code != 200:
            raise RoomNotCreated(room_response.text)
        return room_response.json()["url"]

    def participant_name(self, speaker_id):
        if speaker_id in self.participants:
            return self.participants[speaker_id].name

        return ""

    def add_participant(self, user_id, participant):
        self.has_had_participants = True
        participant.user_id = user_id
        participant.room = self

        if self.is_captioning_active and not participant.is_audience:
            self.manager.add_participant(
                user_id, participant.spoken_language, participant.caption_language
            )
        self.participants[user_id] = participant
        self.logger.log_joined_room(participant)

    def remove_participant(self, user_id):
        if user_id in self.participants:
            participant = self.participants.pop(user_id, None)

            if self.is_captioning_active:
                self.manager.remove_participant(user_id)

            if participant is not None:
                self.logger.log_left_room(participant)

                return True

        return False

    def caption_languages(self):
        return list(set([p.caption_language for p in self.participants.values()]))

    def to_dict(self):
        return {
            "room_id": self.room_id,
            "participants": [p.to_dict() for p in self.participants.values()],
            "settings": self.settings.to_dict(),
        }
