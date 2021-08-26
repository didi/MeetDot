import os
import wave
import numpy as np
from room.participant import Participant
from services.post_translation.interface import (
    PostTranslationRequest,
    PostTranslationResponse,
)
from services.text_to_speech.service import TextToSpeechService


class Chatbot(Participant):
    """
    Chatbot will respond to users with generated TTS audio.
    """

    def __init__(self, language, socketio, on_audio_data, logger):
        super().__init__(
            name="chatbot",
            spoken_language=language,
            caption_language=language,
            is_audience=False,
        )
        self.socketio = socketio
        self.on_audio_data = on_audio_data
        self.tts_model = TextToSpeechService(language)
        self.audio_log_dir = logger.log_dir / "tts_wavs_tmp"
        self.audio_log_dir.mkdir(parents=True, exist_ok=True)

    def __repr__(self):
        return f"{self.name} ( {self.spoken_language})"

    def to_dict(self):
        return {
            k: v
            for k, v in self.__dict__.items()
            if k
            not in ["room", "socketio", "on_audio_data", "tts_model", "audio_log_dir"]
        }

    def on_post_translation(
        self,
        request: PostTranslationRequest,
        response: PostTranslationResponse,
        room_id: str,
    ):
        trans_lan_type = request.language  # language
        if trans_lan_type != self.spoken_language:
            return
        if request.session_id == "chatbot":
            return

        print("received a translation from", request.session_id)

        is_final = request.is_final
        if not is_final:
            return

        trans_text = response.translation
        print(trans_text)

        # this helps accelerate
        self.socketio.start_background_task(self._generate_audio, trans_text, room_id)

    def _generate_audio(self, trans_text, room_id):
        # saved to many wav files.
        wav_file_name = "sample_output.wav"  # randomly generate the string
        out_path = str(self.audio_log_dir / wav_file_name)

        self.tts_model.synthesize(trans_text, save_wav=True, out_path=out_path)
        self._send_to_audio(out_path, room_id)

        # delete the wav file
        os.remove(out_path)

    def _send_to_audio(self, wav_path, room_id):
        # Load wav file
        with wave.open(wav_path) as wav_file:
            i = 0
            chunk_size = 1600
            while i < wav_file.getnframes():
                # Pass chunk by chunk to recognizer
                chunk = wav_file.readframes(chunk_size)  # 1600 is the 1/10 of second
                self.on_audio_data("chatbot", chunk)  # the chuck goes to the listener?
                i += chunk_size
                # Sleep for duration of the chunk, to not overwhelm the streaming ASR

        with open(wav_path, "rb") as wav_file:
            self.socketio.emit(
                "chatbot-audio",
                wav_file.read(),
                room=room_id,
                broadcast=True,
            )
