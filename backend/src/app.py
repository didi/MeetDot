# python sys lib
import base64
import monkey_patch
from services.manager import Manager
from utils import deep_update
import argparse
import os
import ssl
import time
import warnings
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from threading import Timer, stack_size
from traceback import print_exc

# 3rd party modules, pip installed
from dotenv import load_dotenv
from engineio.payload import Payload
from flask import Flask, abort, json, jsonify, request, Response
from flask_cors import CORS
from flask_socketio import SocketIO, join_room
from werkzeug.exceptions import HTTPException

# other repo modules
from namespaces import (
    ChatNamespace,
    FeedbackNamespace,
    ImageTranslationNamespace,
    MeetingNamespace,
    PostMeetingNamespace,
    WordGuessingNamespace,
)
from room import (
    AudienceMember,
    Participant,
    Room,
    RoomType,
    RoomNotCreated,
    RoomList,
    RoomSettings,
)
from services.speech_translation import SpeechTranslationConfig
from services.asr import SpeechRecognitionService
from room.chatbot import Chatbot


class SpeechTranslationServer:
    def __init__(self, translation_config_file, log_dir=Path("logs")):
        self.translation_config_file = translation_config_file

        self.app = Flask(__name__)
        self.app.config["SECRET_KEY"] = "secret!"
        self.app.config["SESSION_COOKIE_NAME"] = "session_name"
        CORS(self.app, cors_allowed_origins="*")
        self.socketio = SocketIO(
            self.app, async_mode="gevent", cors_allowed_origins="*"
        )

        self.log_dir = log_dir / datetime.now().strftime("%Y-%m-%d-%H-%M")
        self.rooms = RoomList(self.socketio)

        # Set up namespaces
        self.namespaces = {
            name: constructor(self.rooms, self.socketio.emit)
            for name, constructor in (
                ("chat", ChatNamespace),
                ("feedback", FeedbackNamespace),
                ("image_translation", ImageTranslationNamespace),
                ("meeting", MeetingNamespace),
                ("post_meeting", PostMeetingNamespace),
                ("word_game", WordGuessingNamespace),
            )
        }
        self.rooms.register_change_listener(
            self.namespaces["word_game"].on_room_changed
        )

        self.setup_rest_endpoints()
        self.setup_socket_endpoints()
        self.setup_error_handlers()

    def delete_if_never_used(self, room, delay_seconds):
        def try_delete_room():
            if room.has_had_participants:
                return

            self.rooms.delete_room(room.room_id)

        timer = Timer(delay_seconds, try_delete_room)
        timer.start()

    def delete_after_max_time(self, room, max_time_seconds):
        def delete_room():
            if len(room.participants) > 0:
                self.socketio.emit(
                    "leave-room",
                    f"Room {room.room_id} has reached maximum duration, please create a new room.",
                    room=room.room_id,
                    broadcast=True,
                )
            self.rooms.delete_room(room.room_id)

        timer = Timer(max_time_seconds, delete_room)
        timer.start()

    def setup_rest_endpoints(self):
        @self.app.route("/rooms", methods=["GET", "POST"])
        @self.app.route("/rooms/<room_id>", methods=["GET"])
        def rooms(room_id=None):
            """
            REST endpoint for meeting rooms
            GET the full list of rooms, or if room_id is specified get just a single room
            POST to create a new meeting room
            """

            if request.method == "GET":
                if room_id is None:
                    return jsonify({"time": time.time(), "rooms": self.rooms.to_list()})
                else:
                    room = self.rooms.get(room_id)

                    if room is not None:
                        room = room.to_dict()

                    return jsonify({"time": time.time(), "room": room})
            elif request.method == "POST":
                # Creating room
                payload = request.json

                if payload["roomId"] in self.rooms:
                    abort(
                        HTTPStatus.CONFLICT,
                        description="A room with that name already exists",
                    )

                ROOM_LIMIT = int(os.getenv("MAX_ROOMS", 10))
                if len(self.rooms) >= ROOM_LIMIT:
                    abort(
                        HTTPStatus.FORBIDDEN,
                        description="Server's meeting limit has been reached, "
                        + "please try again later.",
                    )

                if len(payload["roomId"]) > 20:
                    abort(
                        HTTPStatus.FORBIDDEN,
                        description="Room name must be shorter than 20 characters",
                    )

                if self.translation_config_file:
                    translation_config = SpeechTranslationConfig()
                    translation_config.deep_update_with_json_config(
                        self.translation_config_file
                    )

                    payload_translation_config = payload["settings"].get("services")

                    if payload_translation_config:
                        payload["settings"]["services"] = deep_update(
                            payload["settings"]["services"],
                            {
                                **translation_config.to_dict(),
                                **payload_translation_config,
                            },
                        )
                    else:
                        payload["settings"]["services"] = translation_config.to_dict()

                try:
                    room = Room(
                        room_id=payload["roomId"],
                        room_type=payload["roomType"],
                        log_dir=self.log_dir,
                        socket=self.socketio,
                        settings=payload["settings"],
                    )
                except RoomNotCreated as e:
                    abort(
                        HTTPStatus.BAD_REQUEST,
                        description=f"Could not create room: {e}",
                    )

                if room.settings.interface["chatbot"]["enabled"]:
                    # Create new chatbot if necessary
                    language = room.settings.interface["chatbot"]["language"]
                    participant = Chatbot(
                        language,
                        self.socketio,
                        room.manager.on_audio_data,
                        room.logger,
                    )
                    room.add_participant("chatbot", participant)
                    room.manager.add_post_translation_listener(
                        participant.on_post_translation
                    )

                if room.settings.interface["games"]["word_guessing"]:
                    # Create new game if necessary
                    self.namespaces["word_game"].create_game(room)

                # Start background tasks that will clean up rooms
                EMPTY_ROOM_CLEANUP_TIME_SECONDS = int(
                    os.getenv("EMPTY_ROOM_CLEANUP_TIME_SECONDS", 60 * 5)
                )
                self.socketio.start_background_task(
                    self.delete_if_never_used,
                    room=room,
                    delay_seconds=EMPTY_ROOM_CLEANUP_TIME_SECONDS,
                )
                MAX_ROOM_TIME_SECONDS = int(
                    os.getenv("MAX_ROOM_TIME_SECONDS", 60 * 60 * 2)
                )
                self.socketio.start_background_task(
                    self.delete_after_max_time,
                    room=room,
                    max_time_seconds=MAX_ROOM_TIME_SECONDS,
                )

                if room.is_captioning_active:
                    room.manager.add_transcript_listener(
                        self.namespaces["word_game"].on_transcript
                    )
                    room.manager.add_post_translation_listener(
                        self.namespaces["word_game"].on_translation
                    )
                self.rooms.add_room(room)

                return jsonify({"success": True, "room": room.to_dict()})

        @self.app.route("/settings")
        def settings():
            return jsonify(RoomSettings().to_dict())

        @self.app.route("/lang2asr")
        def lang2asr():
            return jsonify(SpeechRecognitionService.supported_languages_to_providers())

        for ns in self.namespaces.values():
            ns.register_rest_endpoints(self.app)

    def setup_error_handlers(self):
        @self.app.errorhandler(HTTPException)
        def handle_exception(e):
            """Return JSON instead of HTML for certain HTTP errors."""

            # Generic exception handler taken from:
            # https://flask.palletsprojects.com/en/master/errorhandling/#generic-exception-handlers
            response = e.get_response()
            # replace the body with JSON
            response.data = json.dumps(
                {
                    "code": e.code,
                    "name": e.name,
                    "description": e.description,
                }
            )
            response.content_type = "application/json"

            return response

    def setup_socket_endpoints(self):
        @self.socketio.on("on-page")
        def on_page(page_name):
            socket_room_name = page_name

            if page_name.startswith("room/"):
                room_id = page_name.split("/")[1]
                socket_room_name = room_id
            join_room(socket_room_name)
            # TODO: leave_room() is never called, so if
            # a socket (e.g. a browser-tab) redirects from
            # on page/room to another page/room, it will
            # still receive messages from the original page/room.
            # Receiving messages from multiple pages/rooms can cause bugs.
            #
            # We used to have logic that enforced a one-to-one mapping
            # from sockets-to-rooms, but had to get rid of that for the
            # /multi page to work with two rooms that share a socket_id.
            #
            # Moving forward, it may be best to stop creating a flask-room per page,
            # because it doesn't really seem necessary, and simplify this code.  This
            # would involve changes to the /admin page.

        @self.socketio.on("/join")
        def on_joined_room(msg):
            room_id = msg["roomId"]
            room = self.rooms.get(room_id)
            is_audience = msg.get("isAudience")

            if room is None:
                return False, "room not found.", []

            num_participants = sum(
                not p.is_audience for p in room.participants.values()
            )

            if (
                num_participants >= room.settings.interface["max_participants"]
                and not is_audience
            ):
                return False, "room is full.", []

            if len(msg["name"]) == 0:
                return False, "name cannot be empty.", []

            if len(msg["name"]) > 25:
                return False, "name cannot exceed 25 characters.", []

            if "/" in msg["name"]:
                return False, "name must not contain '/'", []

            if is_audience:
                participant = AudienceMember(msg["captionLanguages"])
            else:
                participant = Participant(
                    msg["userId"],
                    msg["spokenLanguage"],
                    msg["captionLanguages"],
                    msg["name"],
                )

            room.add_participant(participant)

            self.rooms.room_changed(room)

            if room.is_captioning_active:
                history = sum(
                    (
                        room.manager.translations.get(lang, [])
                        for lang in msg["captionLanguages"]
                    ),
                    [],
                )
                reactions = room.manager.reactions
            else:
                history, reactions = [], []

            return True, "", history, reactions

        @self.socketio.on("/rejoin")
        def on_rejoined_room(msg):
            if "roomId" not in msg:
                return

            room_id = msg["roomId"]

            room = self.rooms.get(room_id)

            if room is None:
                return

            if msg["userId"] in room.participants:
                join_room(room_id)

        @self.socketio.on("/close")
        def on_close_room(room_id):
            room = self.rooms.get(room_id)

            if room is None:
                return

            if len(room.participants) > 0:
                self.socketio.emit(
                    "leave-room",
                    f"Room {room_id} has been closed by an admin.",
                    room=room_id,
                    broadcast=True,
                )

            self.rooms.delete_room(room_id)

        @self.socketio.on("/spoken-language-changed")
        def on_spoken_language_changed(msg):
            user_id = msg["userId"]
            room_id = msg["roomId"]
            language = msg["language"]

            room = self.rooms.get(room_id)

            if room is None:
                return False

            participant = room.participants.get(user_id)

            if participant is None:
                return False

            room.manager.update_spoken_language(participant.user_id, language)
            participant.spoken_language = language
            self.rooms.room_changed(room)

            return True

        @self.socketio.on("/caption-language-changed")
        def on_caption_language_changed(msg):
            user_id = msg["userId"]
            room_id = msg["roomId"]
            languages = msg["languages"]

            room = self.rooms.get(room_id)

            if room is None:
                return False

            participant = room.participants.get(user_id)

            if participant is None:
                return False

            room.manager.add_new_languages(languages)
            participant.caption_languages = languages
            self.rooms.room_changed(room)

            return True

        @self.socketio.on("/audio/stream")
        def on_audio_stream(msg):
            user_id = msg["userId"]
            room_id = msg["roomId"]

            room = self.rooms.get(room_id)

            if room is None:
                # Edge case: Room was destroyed but some audio messages still get sent

                return

            if user_id not in room.participants:
                # Edge case: user has left the room but some audio messages still get sent

                return

            if room.is_captioning_active:
                chunk = base64.b64decode(
                    msg["data"]
                )  # a arbitrary way to send bytes from backend to frontend
                room.manager.on_audio_data(
                    user_id, chunk, msg.get("end_utterance", False)
                )

        @self.socketio.on("disconnect-user")
        def disconnect_user(msg):
            user_id = msg["userId"]
            rooms_to_delete = []

            for room_id, room in list(self.rooms.items()):
                removed_participant = room.remove_participant(user_id)

                if removed_participant:
                    self.rooms.room_changed(room)

                    if len(room.participants) == 0:
                        # Clean up room if the last participant left
                        rooms_to_delete.append(room_id)

            for room_id in rooms_to_delete:
                self.rooms.delete_room(room_id)

            return True

        @self.socketio.on_error()
        def handle_socket_error(e):
            self.socketio.emit(
                "error", {"name": type(e).__name__, "description": str(e)}
            )
            print_exc()

        for ns in self.namespaces.values():
            ns.register_socket_endpoints(self.socketio)

    def get_certificates(self):
        """
        Tries to get SSL certificates for running in HTTPS

        If you don't have this, need to run on localhost or do browser hacks
        """

        if int(os.getenv("HTTPS_ENABLED", 0)):
            ssl_path = Path(os.getenv("SSL_CERT_PATH"))

            if (ssl_path / "fullchain.pem").exists() and (
                ssl_path / "privkey.pem"
            ).exists():
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(
                    certfile=ssl_path / "fullchain.pem",
                    keyfile=ssl_path / "privkey.pem",
                )

                return context
            else:
                # Certificate doesn't exist locally. Maybe keys were copied from somewhere
                # else (this is fine if you're running locally)
                warnings.warn(
                    "Warning: HTTPS certificate does not exist. HTTPS disabled in env",
                    Warning,
                )
                os.environ["HTTPS_ENABLED"] = "0"

        # Use HTTP
        return None

    def start(self, port, debug):
        ssl_context = self.get_certificates()

        if ssl_context:
            self.socketio.run(
                self.app,
                host="0.0.0.0",
                port=port,
                debug=debug,
                ssl_context=ssl_context,
            )
        else:
            self.socketio.run(self.app, host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="backend server parser settings")
    parser.add_argument(
        "--log_dir", type=Path, default="logs", help="Parent path to save logs"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Speech Translation Configuration File",
    )
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    args = parser.parse_args()

    # Load shared config for frontend and backend
    if not os.path.isfile("../.env"):
        raise FileNotFoundError("could not find .env, run from backend directory")
    load_dotenv(dotenv_path="../.env")

    Payload.max_decode_packets = 50
    server = SpeechTranslationServer(args.config)
    server.start(int(os.getenv("BACKEND_PORT")), args.debug)
