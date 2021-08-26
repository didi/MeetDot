class Namespace:
    def __init__(self, rooms, emit_fn):
        self.rooms = rooms
        self.emit_fn = emit_fn

    def validate(self, room_id, speaker_id):
        room = self.rooms.get(room_id)
        return not (room is None or speaker_id not in room.participants)

    def register_socket_endpoints(self, socketio):
        pass

    def register_rest_endpoints(self, app):
        pass
