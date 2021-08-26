import os
import random
import string
import wave

import gevent
import numpy as np
from speechbrain.pretrained import EncoderClassifier
import torch
import torchaudio

from services.asr import SpeechRecognitionConfig
from .config import LanguageIdConfig
from .model import Wav2Vec2ForSpeechClassification


class LanguageDetector:
    SUPPORTED_LANGUAGES = {"en-US", "zh", "es-ES", "pt-BR"}

    def __init__(self, config: SpeechRecognitionConfig, logger):
        self.active = True
        self.asr_config = config
        self.config = config.language_id
        self.language = config.language
        self.logger = logger
        self.audio_log_dir = logger.log_dir / "langid_wavs_tmp"
        self.audio_log_dir.mkdir(parents=True, exist_ok=True)
        self.model = Wav2Vec2ForSpeechClassification.from_pretrained(self.config.model_path)
        if torch.cuda.is_available():
            self.model = self.model.to("cuda")
        self.model_language_ids = ["zh", "es-ES", "pt-BR", "en-US"]
        self.frames = []

        # Will be overwritten once the first request comes in
        self.session_id = None

        self.vad_model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-vad", model="silero_vad", force_reload=False
        )

    def run(self, update_detected_language):
        sample_rate = self.asr_config.sample_rate_hertz
        chunk_size = self.asr_config.chunk_size
        window_size = self.config.window_size_seconds
        window_stride = self.config.window_stride_seconds

        while self.active:
            if len(self.frames) > (window_size * sample_rate / chunk_size):
                if not self.is_silence(self.frames):
                    # Collected a window worth of samples
                    detected_language, confidence = self.detect(self.frames)
                    self.logger.info(
                        f"Ran language ID and got language {detected_language} "
                        + f"with probability {confidence} (currently {self.language})"
                    )
                    if (
                        detected_language != self.language
                        and detected_language in LanguageDetector.SUPPORTED_LANGUAGES
                        and confidence > self.config.confidence_threshold
                    ):
                        self.language = detected_language
                        self.logger.info(
                            f"Updating detected language to {self.language}"
                        )
                        update_detected_language(self.session_id, self.language)
                else:
                    self.logger.info("VAD heard silence, not running language ID")

                # Carry over overlapping frames to the next time to have a sliding window
                overlapping_frames = int(
                    len(self.frames) * (window_size - window_stride) / window_size
                )
                self.frames = (
                    self.frames[-overlapping_frames:] if overlapping_frames > 0 else []
                )
            else:
                gevent.sleep(chunk_size / sample_rate)

    def frames_to_tensor(self, frames):
        audio_int16 = np.frombuffer(b"".join(frames), np.int16)
        audio_float32 = audio_int16.astype("float32")

        # Normalize
        abs_max = np.abs(audio_int16).max()
        if abs_max > 0:
            audio_float32 *= 1 / abs_max

        audio_float32 = audio_float32.squeeze()  # depends on the use case
        tensor = torch.from_numpy(audio_float32)

        return tensor

    def is_silence(self, frames):
        vad_input = self.frames_to_tensor(frames)
        with torch.no_grad():
            vad_output = self.vad_model(vad_input)
        self.logger.debug(f"Language ID VAD score: {float(vad_output[0, 1])}")
        return vad_output[0, 1] < 0.8

    def save_to_temp_file(self, frames):
        """
        Save frames of audio to a temp file, to be loaded into a tensor
        """
        filename = "".join(random.choice(string.ascii_lowercase) for i in range(10))
        wav_file = str((self.audio_log_dir / f"{filename}.wav").absolute())
        wf = wave.open(wav_file, "wb")
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(self.asr_config.sample_rate_hertz)
        wf.writeframes(b"".join(frames))
        wf.close()
        return wav_file

    def detect(self, frames):
        file_path = self.save_to_temp_file(frames)
        audio_tensor, sample_rate = torchaudio.load(file_path)
        if torch.cuda.is_available():
            audio_tensor = audio_tensor.to("cuda")
        os.remove(file_path)
        predictions = self.model(audio_tensor)[0]
        probs = torch.nn.functional.softmax(predictions, dim=-1)
        max_prob = torch.max(probs)
        top_language_code = self.model_language_ids[int(torch.argmax(probs))]
        return top_language_code, max_prob

    def terminate(self):
        self.active = False

    def __call__(self, session_id, chunk):
        self.session_id = session_id
        self.frames.append(chunk)
