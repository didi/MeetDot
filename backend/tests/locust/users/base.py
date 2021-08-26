import base64
import wave

import gevent
import socketio
from locust import HttpUser


class SpeechTranslationUser(HttpUser):
    # Backend service to connect to
    host = "http://localhost:8000"

    abstract = True

    def on_start(self):
        super().on_start()
        # Initialize websocket
        self.socket = socketio.Client(ssl_verify=False)
        self.socket.connect(SpeechTranslationUser.host)
        self.tasks_completed = 0

    def on_stop(self):
        super().on_stop()
        self.tasks_completed = 0
        gevent.sleep(0.5)
        self.socket.disconnect()

    def send_wav(self, wav_path, user_id, room_id):
        chunk_size = 1600
        sample_rate_hertz = 16000

        with wave.open(wav_path) as wav_file:
            i = 0

            while i < wav_file.getnframes():
                chunk = wav_file.readframes(chunk_size)
                data = base64.b64encode(chunk)

                self.socket.emit(
                    "/audio/stream",
                    {"userId": user_id, "roomId": room_id, "data": data},
                )
                i += chunk_size
                gevent.sleep(chunk_size / sample_rate_hertz)
