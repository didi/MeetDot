"""
Handles events related to chat transcripts
"""

from flask import jsonify

from ..namespace import Namespace


class MeetingNamespace(Namespace):
    def register_socket_endpoints(self, socketio):
        @socketio.on("reaction")
        def on_reaction(msg):
            room_id = msg["roomId"]
            room = self.rooms.get(room_id)
            if not room:
                return

            # Add reactions to a data structure, so that new people can get it too
            room.manager.reactions[msg["messageId"]][msg["userId"]] = msg["reaction"]
            self.emit_fn("reaction", msg, room=room_id)

    def register_rest_endpoints(self, app):
        @app.route("/history/<room_id>/<lang>", methods=["GET"])
        def get_history(room_id, lang):
            room = self.rooms.get(room_id)
            return jsonify(room.manager.translations[lang])
