import time

from unittest import mock

from namespaces import PostMeetingNamespace
from room import Participant, Room, RoomList, RoomType


def test_manager():
    room = Room(
        room_id="abc",
        room_type=RoomType.LIVE,
        log_dir="logs/test",
        socket=mock.Mock(),
    )

    room.add_participant(Participant("person1", "en-US", ["en-US"]))

    # Test that sending data works
    room.manager.on_text_data("person1", "Hello", "en-US")
    time.sleep(0.02)  # just to generate new message_ids
    room.manager.on_text_data("person1", "Goodbye", "en-US")

    # Test that downloading transcript works
    rlist = RoomList(mock.Mock())
    rlist.add_room(room)
    ns = PostMeetingNamespace(rlist, None)
    ns.register_rest_endpoints(mock.Mock(route=lambda *args, **kwargs: lambda y: y))

    time.sleep(0.1)  # wait for pipeline to finish
    result = ns.download_history("abc", "en-US")

    assert (
        str(result.data.decode("utf-8"))
        == "person1 (en-US): Hello\n\nperson1 (en-US): Goodbye\n"
    )

    # Now person1 says something in zh, a language that hasn't been used yet
    room.manager.on_text_data("person1", "你好吗", "zh")
    time.sleep(0.5)  # wait longer because these ones involve translation

    result = ns.download_history("abc", "en-US")
    assert "how are you" in result.data.decode("utf-8").lower()

    # Test the catchup translator. This works, but causes a non-fatal error
    # because the catchup translator isn't cleaned properly.
    # I'm leaving this in for now, hopefully switching stuff to async fixes it

    # # person2 joins with chinese captions, and should see captions in zh
    # room.add_participant(Participant("person2", "zh", ["zh"]))
    # room.manager.on_text_data("person2", "高兴", "zh")
    # time.sleep(1) # wait longer because this calls the catchup translator

    # result = ns.download_history("abc", "en-US")
    # assert "happy" in result.data.decode("utf-8").lower()
    # result_zh = ns.download_history("abc", "zh")
    # assert "再见" in result_zh.data.decode("utf-8").lower()

    # Clean up
    room.manager.speech_translator.mt_service.end_session("person1", False)
    room.manager.speech_translator.mt_service.end_session("person2", False)
