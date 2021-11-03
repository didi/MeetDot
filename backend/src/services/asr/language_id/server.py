import argparse
import asyncio
import concurrent
import json
import logging
import os
from pathlib import Path
import random
import string
import wave
import websockets

import numpy as np
import torch
import torchaudio

from language_id_config import LanguageIdConfig
from model import Wav2Vec2ForSpeechClassification

CACHE_CLEAR_THRESHOLD = 2**30 * 2 # 2 Gigabytes

class LanguageIdentifier:
    LANGUAGE_ID_MAPPING = ["en-US", "es-ES", "pt-BR", "zh"]

    def __init__(
        self, model, vad_model, config, initial_language, sample_rate_hertz, chunk_size
    ):
        self.config = LanguageIdConfig(**config)
        self.sample_rate = sample_rate_hertz
        self.chunk_size = chunk_size
        self.num_consecutive = 0
        self.language = initial_language
        self.last_language = initial_language
        self.frames = []
        self.audio_log_dir = Path(__file__).parent / "langid_wavs_tmp"
        self.audio_log_dir.mkdir(parents=True, exist_ok=True)
        self.model = model
        self.vad_model = vad_model

    def process_chunk(self, chunk):
        self.frames.append(chunk)
        if len(self.frames) > (
            self.config.window_size_seconds * self.sample_rate / self.chunk_size
        ):
            newly_detected_language = None
            # Collected a window worth of samples
            if not self.is_silence(self.frames):
                detected_language, confidence = self.detect(self.frames)

                if detected_language == self.last_language:
                    self.num_consecutive = self.num_consecutive + 1
                else:
                    self.num_consecutive = 1
                logger.info(
                    f"Ran language ID and got language {detected_language} "
                    + f"with probability {confidence} (currently {self.language}). "
                    + f"{self.num_consecutive} in a row."
                )
                self.last_language = detected_language

                if (
                    detected_language != self.language
                    and confidence > self.config.confidence_threshold
                    and self.num_consecutive >= self.config.num_consecutive_threshold
                ):
                    self.language = detected_language
                    logger.info(f"Updating detected language to {self.language}")
                    newly_detected_language = self.language
            else:
                logger.info("VAD heard silence, not running language ID")
                self.num_consecutive = 0
                self.last_language = None

            # Carry over overlapping frames to the next time to have a sliding window
            overlapping_frames = int(
                len(self.frames)
                * (self.config.window_size_seconds - self.config.window_stride_seconds)
                / self.config.window_size_seconds
            )
            self.frames = (
                self.frames[-overlapping_frames:] if overlapping_frames > 0 else []
            )

            if torch.cuda.is_available() and \
                    torch.cuda.memory_reserved() + torch.cuda.memory_allocated() >= CACHE_CLEAR_THRESHOLD:
                torch.cuda.empty_cache()

            if newly_detected_language is not None:
                return newly_detected_language

    def detect(self, frames):
        file_path = self.save_to_temp_file(frames)
        audio_tensor, sample_rate = torchaudio.load(file_path)
        if torch.cuda.is_available():
            audio_tensor = audio_tensor.to("cuda")
        os.remove(file_path)
        predictions = self.model(audio_tensor)[0]
        probs = torch.nn.functional.softmax(predictions, dim=-1)
        max_prob = torch.max(probs)
        top_language_code = LanguageIdentifier.LANGUAGE_ID_MAPPING[
            int(torch.argmax(probs))
        ]
        return top_language_code, max_prob.cpu()

    def save_to_temp_file(self, frames):
        """
        Save frames of audio to a temp file, to be loaded into a tensor
        """
        filename = "".join(random.choice(string.ascii_lowercase) for i in range(10))
        wav_file = str((self.audio_log_dir / f"{filename}.wav").absolute())
        wf = wave.open(wav_file, "wb")
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(self.sample_rate)
        wf.writeframes(b"".join(frames))
        wf.close()
        return wav_file

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
        logger.debug(f"Language ID VAD score: {float(vad_output[0, 1])}")
        return vad_output[0, 1] < 0.8


def load_model(model_path):
    model = Wav2Vec2ForSpeechClassification.from_pretrained(model_path)
    if torch.cuda.is_available():
        model = model.to("cuda")
    vad_model, _ = torch.hub.load(
        repo_or_dir="snakers4/silero-vad", model="silero_vad", force_reload=False
    )
    return model, vad_model


async def recognize(websocket, path):
    language_id, config = None, None

    while True:
        try:
            message = await websocket.recv()
        except websockets.exceptions.ConnectionClosedError:
            logging.info("Client closed socket")
            break

        if isinstance(message, str) and "config" in message:
            # Load configuration if provided

            msg = json.loads(message)
            config = msg.get("config", {})
            initial_language = msg.get("language", "en-US")
            sample_rate_hertz = msg.get("sample_rate_hertz", 16000)
            chunk_size = msg.get("chunk_size", 1600)
            continue
        elif message == '{"eof" : 1}':
            await websocket.send("")
            break

        if not language_id:
            assert config is not None, "Need to send config as first message"
            language_id = LanguageIdentifier(
                model,
                vad_model,
                config,
                initial_language,
                sample_rate_hertz,
                chunk_size,
            )

        predicted_language = await loop.run_in_executor(
            pool, language_id.process_chunk, message
        )

        # Only send on language updates
        if predicted_language is not None:
            try:
                await websocket.send(
                    json.dumps({"detected_language": predicted_language})
                )
            except websockets.exceptions.ConnectionClosedOK:
                logging.info("Socket was closed before last message sent, handled")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=3500)
    parser.add_argument(
        "--model_path", type=str, default="src/services/asr/language_id/models/best"
    )
    parser.add_argument("--num_threads", type=int, default=10)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--save_logs", type=bool, default=False)

    args = parser.parse_args()
    if args.save_logs:
        logging.basicConfig(
            filename="logs/language_id_server.log",
            format="%(asctime)s %(message)s",
            filemode="w",
        )
    logger = logging.getLogger("websockets")
    logger.setLevel(level=logging.DEBUG if args.verbose else logging.INFO)
    logger.addHandler(logging.StreamHandler())

    model, vad_model = load_model(args.model_path)

    logger.info(f"Loaded language ID model: {model}")
    pool = concurrent.futures.ThreadPoolExecutor((args.num_threads or 1))
    loop = asyncio.get_event_loop()

    start_server = websockets.serve(recognize, args.host, args.port)

    logger.info(f"Starting language ID server at {args.host}:{args.port}")
    loop.run_until_complete(start_server)
    loop.run_forever()
