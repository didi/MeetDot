import os
import time

import requests

from .room import RoomType


class RoomList:
    def __init__(self, socketio):
        self.socketio = socketio
        self.rooms = {}
        self._change_listeners = []
        self._publish_rooms_to_admin()

    def room_changed(self, room):
        self.socketio.emit(
            "room",
            {"time": time.time(), "room": room.to_dict()},
            room=room.room_id,
            broadcast=True,
        )
        self._publish_rooms_to_admin()

        # Notify listeners of change
        for listener in self._change_listeners:
            listener(room)

    def register_change_listener(self, listener):
        self._change_listeners.append(listener)

    def add_room(self, room):
        self.rooms[room.room_id] = room
        self._publish_rooms_to_admin()

    def delete_room(self, room_id):
        room = self.rooms.get(room_id)
        if room is None:
            return

        if room.room_type == RoomType.MEETING:
            DAILY_ENDPOINT = os.getenv("DAILY_API_BASE_URL") + f"/rooms/{room_id}"
            DAILY_AUTH_KEY = os.getenv("DAILY_API_AUTH_KEY")

            room_response = requests.delete(
                url=DAILY_ENDPOINT,
                headers={"Authorization": f"Bearer {DAILY_AUTH_KEY}"},
            )
            if room_response.status_code != 200:
                return

        self.rooms.pop(room_id, None)
        self.socketio.emit(
            "room",
            {"time": time.time(), "room": None},
            room=room_id,
            broadcast=True,
        )
        self._publish_rooms_to_admin()

    def _publish_rooms_to_admin(self):
        self.socketio.emit(
            "rooms",
            {"time": time.time(), "rooms": [r.to_dict() for r in self.rooms.values()]},
            room="admin",
            broadcast=True,
        )

    def to_list(self):
        return [r.to_dict() for r in self.rooms.values()]

    def items(self):
        return self.rooms.items()

    def get(self, room_id, default=None):
        return self.rooms.get(room_id, default)

    def __contains__(self, item):
        return item in self.rooms

    def __len__(self):
        return len(self.rooms)
