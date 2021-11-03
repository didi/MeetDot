from ..namespace import Namespace


class ChatNamespace(Namespace):
    def register_socket_endpoints(self, socketio):
        @socketio.on("chat")
        def on_chat(msg):
            room_id = msg["roomId"]
            room = self.rooms.get(room_id)
            if not room:
                return

            room.manager.on_text_data(msg["userId"], msg["text"], msg["language"])

        # Bind all the socket methods so they can be called for testing
        ChatNamespace.on_chat = staticmethod(on_chat)
