# Tests Flask and Socketio endpoints
import json
import random
import re
import string
import pytest

from app import SpeechTranslationServer


# Helpers
def parse(response):
    """Convert response to JSON"""
    return json.loads(response.get_data(as_text=True))


def camel_to_snake(word):
    """Convert CamelCase to snake_case"""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", word).lower()


# Fixtures
# If this file gets large, this can go in backend/conftest.py
@pytest.fixture
def clients():
    server = SpeechTranslationServer(None)
    server.app.testing = True
    flask_client = server.app.test_client()
    socket_client = server.socketio.test_client(server.app)

    return [flask_client, socket_client]


# Tests
def test_join(clients):
    flask_client, socket_client = clients

    # Get the list of rooms, should be empty
    response = parse(flask_client.get("rooms"))
    assert "time" in response
    assert response["rooms"] == []

    # Create two rooms
    room_name_one = "".join(random.choice(string.ascii_lowercase) for i in range(8))
    flask_client.post(
        "rooms",
        json={
            "roomId": room_name_one,
            "roomType": "live",
            "settings": {},
        },
    )
    room_name_two = "".join(random.choice(string.ascii_lowercase) for i in range(8))
    flask_client.post(
        "rooms",
        json={
            "roomId": room_name_two,
            "roomType": "live",
            "settings": {},
        },
    )

    # Check that the rooms exist
    from room.room_settings import RoomSettings

    room_list = parse(flask_client.get("rooms"))["rooms"]

    assert room_list[0] == {
        "room_id": room_name_one,
        "participants": [],
        "settings": RoomSettings().to_dict(),
    }
    assert room_list[1] == {
        "room_id": room_name_two,
        "participants": [],
        "settings": RoomSettings().to_dict(),
    }

    # Join a room
    person1 = {
        "name": "person1",
        "spokenLanguage": "en-US",
        "captionLanguage": "es",
        "userId": "user1",
        "roomId": room_name_two,
    }
    socket_client.emit("/join", person1)

    # Check that someone is in the room
    room_list = parse(flask_client.get("rooms"))["rooms"]
    assert room_list[1]["participants"] == [
        {
            "name": "person1",
            "spoken_language": "en-US",
            "caption_language": "es",
            "user_id": "user1",
            "is_audience": False,
        }
    ]

    # Leave a room
    socket_client.emit("disconnect-user", {"userId": "user1"})

    # Check that room 1 is automatically closed
    room_list = parse(flask_client.get("rooms"))["rooms"]
    assert len(room_list) == 1

    # Close room
    socket_client.emit("/close", room_name_one)

    # Check that room 1 is closed
    room_list = parse(flask_client.get("rooms"))["rooms"]
    assert len(room_list) == 0
