import random
from pathlib import Path
from unittest import mock

import pytest
from room.participant import Participant
from room.room import Room, RoomType
from services.captioning import CaptioningRequest

from namespaces import WordGuessingNamespace


def test_word_guessing():
    """Test socket endpoints for the word guessing game without translation"""

    # Fake socket that intercepts calls
    roles = {}

    def emit_fn(endpoint, data, **kwargs):
        if endpoint == "round-started":
            roles.update(data["roles"])

    # Test room flow
    room = Room(
        room_id="abc",
        room_type=RoomType.LIVE,
        log_dir=Path("logs/test"),
        socket=mock.Mock(),
    )
    room.add_participant(Participant("player1", "en-US", ["en-US"]))
    room.add_participant(Participant("player2", "en-US", ["en-US"]))

    word_game_namespace = WordGuessingNamespace({"abc": room}, emit_fn)
    word_game_namespace.register_socket_endpoints(mock.Mock(on=lambda x: lambda y: y))

    word_game_namespace.create_game(room)
    word_game_namespace.on_player_joined({"roomId": "abc", "userId": "player1"})
    word_game_namespace.on_player_ready({"roomId": "abc", "userId": "player1"})

    word_game_namespace.on_player_joined({"roomId": "abc", "userId": "player2"})
    word_game_namespace.on_player_ready({"roomId": "abc", "userId": "player2"})

    giver = "player1" if roles["player1"] == "giver" else "player2"
    guesser = "player1" if roles["player1"] == "guesser" else "player2"
    word = word_game_namespace.games["abc"].displayed_word

    # Create an utterance not containing any words
    word_game_namespace.on_transcript(
        mock.Mock(session_id=guesser), mock.Mock(transcript="zzzzzzzz"), "abc"
    )
    assert word_game_namespace.games["abc"].round_score == {
        giver: {
            "described": 0,
            "guessed": 0,
            "penalized": 0,
            "skipped": 0,
            "total_score": 0,
        },
        guesser: {
            "described": 0,
            "guessed": 0,
            "penalized": 0,
            "skipped": 0,
            "total_score": 0,
        },
    }

    # Create an utterance where the giver says the word, penalize them
    word_game_namespace.on_transcript(
        mock.Mock(session_id=giver), mock.Mock(transcript=word), "abc"
    )
    assert word_game_namespace.games["abc"].round_score == {
        giver: {
            "described": 0,
            "guessed": 0,
            "penalized": 1,
            "skipped": 0,
            "total_score": -1,
        },
        guesser: {
            "described": 0,
            "guessed": 0,
            "penalized": 0,
            "skipped": 0,
            "total_score": 0,
        },
    }

    # Create an utterance where the guesser says the word
    word = word_game_namespace.games["abc"].displayed_word
    word_game_namespace.on_transcript(
        mock.Mock(session_id=guesser), mock.Mock(transcript=word), "abc"
    )
    assert word_game_namespace.games["abc"].round_score == {
        giver: {
            "described": 1,
            "guessed": 0,
            "penalized": 1,
            "skipped": 0,
            "total_score": 0,
        },
        guesser: {
            "described": 0,
            "guessed": 1,
            "penalized": 0,
            "skipped": 0,
            "total_score": 1,
        },
    }

    # Test skip
    word_game_namespace.on_skip_word({"roomId": "abc", "userId": guesser})
    assert word_game_namespace.games["abc"].round_score == {
        giver: {
            "described": 1,
            "guessed": 0,
            "penalized": 1,
            "skipped": 1,
            "total_score": 0,
        },
        guesser: {
            "described": 0,
            "guessed": 1,
            "penalized": 0,
            "skipped": 0,
            "total_score": 1,
        },
    }

    # Clean up

    for p in list(room.participants.keys()):
        room.remove_participant(p)


def test_guessing_with_translation():
    # Fake socket that intercepts calls
    roles = {}

    def emit_fn(endpoint, data, **kwargs):
        if endpoint == "round-started":
            roles.update(data["roles"])

    # Test room flow
    room = Room(
        room_id="abc",
        room_type=RoomType.LIVE,
        log_dir=Path("logs/test"),
        socket=mock.Mock(),
    )
    room.add_participant(Participant("player1", "en-US", ["en-US"]))
    room.add_participant(Participant("player2", "zh", ["zh"]))

    word_game_namespace = WordGuessingNamespace({"abc": room}, emit_fn)
    word_game_namespace.register_socket_endpoints(mock.Mock(on=lambda x: lambda y: y))

    word_game_namespace.create_game(room)
    word_game_namespace.on_player_joined({"roomId": "abc", "userId": "player1"})
    word_game_namespace.on_player_ready({"roomId": "abc", "userId": "player1"})
    word_game_namespace.on_player_joined({"roomId": "abc", "userId": "player2"})
    word_game_namespace.on_player_ready({"roomId": "abc", "userId": "player2"})

    giver = "player1" if roles["player1"] == "giver" else "player2"
    guesser = "player1" if roles["player1"] == "guesser" else "player2"
    giver_lang = room.participants[giver].spoken_language
    guesser_lang = room.participants[guesser].spoken_language

    # Create an utterance not containing any words
    word_game_namespace.on_translation(
        mock.Mock(language=giver_lang, session_id=guesser),
        mock.Mock(translation="zzzzzzzz"),
        "abc",
    )
    assert word_game_namespace.games["abc"].round_score == {
        giver: {
            "described": 0,
            "guessed": 0,
            "penalized": 0,
            "skipped": 0,
            "total_score": 0,
        },
        guesser: {
            "described": 0,
            "guessed": 0,
            "penalized": 0,
            "skipped": 0,
            "total_score": 0,
        },
    }

    # Create an utterance where the giver says the word
    word = word_game_namespace.games[
        "abc"
    ].displayed_word  # fake translation by passing the giver word directly
    word_game_namespace.on_translation(
        mock.Mock(language=guesser_lang, session_id=giver),
        mock.Mock(translation=word),
        "abc",
    )
    assert word_game_namespace.games["abc"].round_score == {
        giver: {
            "described": 0,
            "guessed": 0,
            "penalized": 0,
            "skipped": 0,
            "total_score": 0,
        },
        guesser: {
            "described": 0,
            "guessed": 0,
            "penalized": 0,
            "skipped": 0,
            "total_score": 0,
        },
    }

    # Create an utterance where the guesser says the word
    word_game_namespace.on_translation(
        mock.Mock(language=giver_lang, session_id=guesser),
        mock.Mock(translation=word),
        "abc",
    )
    assert word_game_namespace.games["abc"].round_score == {
        giver: {
            "described": 1,
            "guessed": 0,
            "penalized": 0,
            "skipped": 0,
            "total_score": 1,
        },
        guesser: {
            "described": 0,
            "guessed": 1,
            "penalized": 0,
            "skipped": 0,
            "total_score": 1,
        },
    }

    # Test skip
    word_game_namespace.on_skip_word({"roomId": "abc", "userId": guesser})
    assert word_game_namespace.games["abc"].round_score == {
        giver: {
            "described": 1,
            "guessed": 0,
            "penalized": 0,
            "skipped": 1,
            "total_score": 1,
        },
        guesser: {
            "described": 0,
            "guessed": 1,
            "penalized": 0,
            "skipped": 0,
            "total_score": 1,
        },
    }

    # Clean up

    for p in list(room.participants.keys()):
        room.remove_participant(p)


def test_multiple_guessers_game():
    # Fake socket that intercepts calls, test multiple players play multilingual taboo game.

    roles = {}

    def emit_fn(endpoint, data, **kwargs):
        if endpoint == "round-started":
            roles.update(data["roles"])

    # Test room flow
    room_id = "multi-player-test"

    room = Room(
        room_id=room_id,
        room_type=RoomType.LIVE,
        log_dir=Path("logs/test"),
        socket=mock.Mock(),
    )
    room.add_participant(Participant("player-en", "en-US", ["en-US"]))
    room.add_participant(Participant("player-zh", "zh", ["zh"]))
    room.add_participant(Participant("player-es", "es-ES", ["es-ES"]))

    # first round
    word_game_namespace = WordGuessingNamespace({room_id: room}, emit_fn)
    word_game_namespace.register_socket_endpoints(mock.Mock(on=lambda x: lambda y: y))

    word_game_namespace.create_game(room)
    word_game_namespace.on_player_joined({"roomId": room_id, "userId": "player-en"})
    word_game_namespace.on_player_ready({"roomId": room_id, "userId": "player-en"})
    word_game_namespace.on_player_joined({"roomId": room_id, "userId": "player-zh"})
    word_game_namespace.on_player_ready({"roomId": room_id, "userId": "player-zh"})
    word_game_namespace.on_player_joined({"roomId": room_id, "userId": "player-es"})
    word_game_namespace.on_player_ready({"roomId": room_id, "userId": "player-es"})
    assert word_game_namespace.games[room_id].round_score == {
        "player-en": {
            "described": 0,
            "skipped": 0,
            "total_score": 0,
            "guessed": 0,
            "penalized": 0,
        },
        "player-zh": {
            "described": 0,
            "skipped": 0,
            "total_score": 0,
            "guessed": 0,
            "penalized": 0,
        },
        "player-es": {
            "described": 0,
            "skipped": 0,
            "total_score": 0,
            "guessed": 0,
            "penalized": 0,
        },
    }
    assert word_game_namespace.games[room_id].finished_givers_set == set()

    giver = word_game_namespace.games[room_id].giver
    word_game_namespace.games[room_id].end_round()

    assert word_game_namespace.games[room_id].game_score == {
        "player-en": {
            "described": 0,
            "guessed": 0,
            "penalized": 0,
            "skipped": 0,
            "total_score": 0,
        },
        "player-zh": {
            "described": 0,
            "guessed": 0,
            "penalized": 0,
            "skipped": 0,
            "total_score": 0,
        },
        "player-es": {
            "described": 0,
            "guessed": 0,
            "penalized": 0,
            "skipped": 0,
            "total_score": 0,
        },
    }

    # second round
    word_game_namespace.on_player_ready({"roomId": room_id, "userId": "player-en"})
    word_game_namespace.on_player_ready({"roomId": room_id, "userId": "player-zh"})
    word_game_namespace.on_player_ready({"roomId": room_id, "userId": "player-es"})

    giver = word_game_namespace.games[room_id].giver
    guessers = word_game_namespace.games[room_id].guessers

    # Create an utterance not containing any words

    for guesser in guessers:
        word_game_namespace.on_translation(
            mock.Mock(language=giver.spoken_language, session_id=guesser.user_id),
            mock.Mock(translation="zzzzzzzz"),
            room_id,
        )

    # Create an utterance where the giver says the word
    word = word_game_namespace.games[room_id].displayed_word  # giver say word directly
    word_game_namespace.on_transcript(
        mock.Mock(language=giver.spoken_language, session_id=giver.user_id),
        mock.Mock(transcript=word),
        room_id,
    )
    word_game_namespace.games[room_id].end_round()

    assert len(word_game_namespace.games[room_id].finished_givers_set) == 2
    assert (
        sum(
            [
                v["total_score"]
                for k, v in word_game_namespace.games[room_id].game_score.items()
            ]
        )
        == -1
    )

    # third round
    word_game_namespace.on_player_ready({"roomId": room_id, "userId": "player-en"})
    word_game_namespace.on_player_ready({"roomId": room_id, "userId": "player-zh"})
    word_game_namespace.on_player_ready({"roomId": room_id, "userId": "player-es"})

    giver = word_game_namespace.games[room_id].giver
    guessers = word_game_namespace.games[room_id].guessers

    # Create an utterance where the guesser says the word

    for i in range(3):
        word = word_game_namespace.games[room_id].displayed_word
        guesser = random.choice(guessers)
        word_game_namespace.on_translation(
            mock.Mock(language=giver.spoken_language, session_id=guesser.user_id),
            mock.Mock(translation=word),
            room_id,
        )
    assert (
        sum(
            [
                v["guessed"]
                for k, v in word_game_namespace.games[room_id].round_score.items()
            ]
        )
        == 3
    )

    word_game_namespace.games[room_id].end_round()

    assert len(word_game_namespace.games[room_id].finished_givers_set) == 3
    assert (
        sum(
            [
                v["total_score"]
                for k, v in word_game_namespace.games[room_id].game_score.items()
            ]
        )
        == 5
    )
    # Clean up

    for p in list(room.participants.keys()):
        room.remove_participant(p)
