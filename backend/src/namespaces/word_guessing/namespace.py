from services.asr import SpeechRecognitionRequest, SpeechRecognitionResponse
from services.post_translation import PostTranslationRequest, PostTranslationResponse

from .game import WordGuessingGame, WordGameState
from ..namespace import Namespace


class WordGuessingNamespace(Namespace):
    def __init__(self, rooms, emit_fn):
        super().__init__(rooms, emit_fn)
        self.rooms = rooms
        self.emit_fn = emit_fn
        self.games = {}

    def on_room_changed(self, room):
        game = self.games.get(room.room_id)

        if game is None:
            return
        game.players_changed()

    def create_game(self, room):
        self.games[room.room_id] = WordGuessingGame(
            room.participants,
            emit_fn=lambda event, msg: self.emit_fn(
                event, msg, room=room.room_id, broadcast=True
            ),
            logger=room.logger,
        )

    def on_transcript(
        self,
        request: SpeechRecognitionRequest,
        response: SpeechRecognitionResponse,
        room_id: str,
    ):
        if not self.validate(room_id, request.session_id) or room_id not in self.games:
            return

        self.games[room_id].on_transcript(request.session_id, response.transcript)

    def on_translation(
        self,
        request: PostTranslationRequest,
        response: PostTranslationResponse,
        room_id: str,
    ):
        if not self.validate(room_id, request.session_id) or room_id not in self.games:
            return

        self.games[room_id].on_translation(
            request.session_id,
            request.language,
            response.translation,
        )

    def register_socket_endpoints(self, socketio):
        @socketio.on("player-joined")
        def on_player_joined(msg):
            game = self.games.get(msg["roomId"])

            if game is None:
                return

            data = {"state": game.game_state}
            if game.game_state == WordGameState.ROUND_ACTIVE:
                game.guessers.append(game.participants[msg["userId"]])
                # TODO: update word bank with new language if needed
                data["start_time"] = game.start_time
                data["end_time"] = game.end_time
                data["max_skips"] = game.max_skips
                data["roles"] = {p: r.value for p, r in game.players_to_roles.items()}
                data["word"] = game.displayed_word
                data["round_number"] = len(game.rounds) + 1
                data["round_score"] = game.round_score
                data["game_score"] = game.game_score
            elif game.game_state in (
                WordGameState.ROUND_FINISHED,
                WordGameState.GAME_FINISHED,
            ):
                data["round_number"] = len(game.rounds) + 1
                data["round_score"] = game.round_score
                data["game_score"] = game.game_score

            return data

        @socketio.on("play-again")
        def on_play_again(msg):
            room_id = msg["roomId"]

            if room_id not in self.games:
                return

            self.games[room_id].restart_if_necessary()

        @socketio.on("player-ready")
        def on_player_ready(msg):
            room_id = msg["roomId"]

            if not self.validate(room_id, msg["userId"]):
                return

            room = self.rooms.get(room_id)
            game = self.games.get(room_id)

            if game is None:
                return

            game.player_ready(msg["userId"])

            if game.ready_to_start:
                # Start game once everybody in the room has confirmed
                start_info = game.start_round(
                    room.settings.interface["games"]["game_duration"]
                )

                self.emit_fn("round-started", start_info, room=room_id, broadcast=True)

        @socketio.on("skip-word")
        def on_skip_word(msg):
            room_id = msg["roomId"]

            if not self.validate(room_id, msg["userId"]):
                return

            if room_id in self.games:
                self.games[room_id].skip_word()

        @socketio.on("end-round")
        def on_end_round(msg):
            room_id = msg["roomId"]

            if not self.validate(room_id, msg["userId"]):
                return

            if room_id in self.games:
                self.games[room_id].end_round()

        # Bind all the socket methods so they can be called locally
        WordGuessingNamespace.on_player_joined = staticmethod(on_player_joined)
        WordGuessingNamespace.on_play_again = staticmethod(on_play_again)
        WordGuessingNamespace.on_player_ready = staticmethod(on_player_ready)
        WordGuessingNamespace.on_skip_word = staticmethod(on_skip_word)
        WordGuessingNamespace.on_end_round = staticmethod(on_end_round)
