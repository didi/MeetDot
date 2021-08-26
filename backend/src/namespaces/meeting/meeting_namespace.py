"""
Handles events related to chat transcripts
"""

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
