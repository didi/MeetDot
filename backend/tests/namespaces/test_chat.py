"""Test chat, but also some features of the manager"""

import time
from unittest import mock

import pytest
from room.participant import Participant
from room.room import Room, RoomType

from namespaces import ChatNamespace


def test_chat():
    room = Room(
        room_id="abc",
        room_type=RoomType.LIVE,
        log_dir="logs/test",
        socket=mock.Mock(),
    )
    room.add_participant(Participant("person1", "en-US", ["en-US"]))
    room.add_participant(Participant("person2", "zh", ["zh"]))

    chat_namespace = ChatNamespace({"abc": room}, None)
    chat_namespace.register_socket_endpoints(mock.Mock(on=lambda x: lambda y: y))

    chat_namespace.on_chat(
        {
            "roomId": "abc",
            "userId": "person1",
            "text": "Hello",
            "language": "en-US",
        }
    )

    time.sleep(0.5)  # delay so translation server can process the data

    assert room.manager.transcript == []
    assert room.manager.chat_history[0].text == "Hello"
    assert room.manager.translations["en-US"][0]["text"] == "Hello"
    assert room.manager.translations["zh"][0]["text"] == "你好"

    chat_namespace.on_chat(
        {"roomId": "abc", "userId": "person2", "text": "再见", "language": "zh"}
    )
    time.sleep(0.5)

    assert room.manager.transcript == []
    assert room.manager.chat_history[1].text == "再见"
    assert room.manager.translations["en-US"][1]["text"] == "Goodbye"
    assert room.manager.translations["zh"][1]["text"] == "再见"

    # Clean up
    room.manager.speech_translator.mt_service.end_session("person1", False)
    room.manager.speech_translator.mt_service.end_session("person2", False)
