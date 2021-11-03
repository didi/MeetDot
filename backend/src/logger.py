import json
import logging
import re
import wave
from pathlib import Path


class Logger:
    CONFIG_LOG_FILENAME = "config.json"
    MAIN_LOG_FILENAME = "main.log"
    CONVERSATION_LOG_FILENAME = "conversation.log"

    def __init__(
        self, log_dir: Path, get_participant_name, room_config, log_level=logging.INFO
    ):
        self.room_config = room_config
        self.get_participant_name = get_participant_name

        # Set up main log dir

        if log_dir.exists():
            # Find log dir that doesn't overwrite existing room

            while log_dir.exists():
                match = re.match("(.*_)([0-9]+)", log_dir.stem)

                if match is not None:
                    stem, counter = match.groups()
                    log_dir = log_dir.parent / (stem + f"{int(counter) + 1}")
                else:
                    log_dir = log_dir.parent / (log_dir.stem + "_1")

        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = log_dir

        # Set up audio recording logging
        self.audio_log_dir = log_dir / "audio"
        self.audio_log_dir.mkdir(parents=True, exist_ok=True)
        self.audio_files = {}

        # Set up main logger
        self.main_logger = logging.getLogger(str(log_dir.absolute()))
        self.main_logger.setLevel(log_level)
        handler = logging.FileHandler(self.log_dir / Logger.MAIN_LOG_FILENAME)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        )
        self.main_logger.addHandler(handler)

        # Set up main logger
        self.conversation_logger = logging.getLogger(
            str((log_dir / "transcript").absolute())
        )
        self.conversation_logger.setLevel(log_level)
        handler = logging.FileHandler(self.log_dir / Logger.CONVERSATION_LOG_FILENAME)
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        self.conversation_logger.addHandler(handler)

        # Set up word game logger
        self.word_game_log_dir = self.log_dir / "words"
        self.word_game_log_dir.mkdir(parents=True, exist_ok=True)
        self.word_game_logger = logging.getLogger(
            str(self.word_game_log_dir.absolute())
        )
        self.word_game_logger.setLevel(log_level)
        handler = logging.FileHandler(self.word_game_log_dir / Logger.MAIN_LOG_FILENAME)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        )
        self.word_game_logger.addHandler(handler)

        # Save the room config
        with open(log_dir / Logger.CONFIG_LOG_FILENAME, "w") as config_file:
            json.dump(room_config.to_dict(), config_file, indent=2, sort_keys=True)

    def info(self, *args, **kwargs):
        return self.main_logger.info(*args, **kwargs)

    def debug(self, *args, **kwargs):
        return self.main_logger.debug(*args, **kwargs)

    def warning(self, *args, **kwargs):
        return self.main_logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        return self.main_logger.error(*args, **kwargs)

    def log_joined_room(self, participant):
        self.main_logger.info(f"{participant} joined the room.")
        self.conversation_logger.info(f"{participant} joined the room.")

    def log_left_room(self, participant):
        self.main_logger.info(f"{participant} left the room.")
        self.conversation_logger.info(f"{participant} left the room.")

    def log_utterance(self, speaker, language, utterance, translations):
        self.conversation_logger.info(f"{speaker} ({language}) said: {utterance}")
        padding_base_length = len(speaker) + 5
        for target_language, translation in translations:
            padding = " " * (padding_base_length + len(language) - len(target_language))
            self.conversation_logger.info(
                f"{padding} ({target_language}): {translation}"
            )

    def log_audio_chunk(self, speaker_id, chunk):
        if speaker_id not in self.audio_files:
            sample_rate = self.room_config.services.asr.sample_rate_hertz
            wave_file = wave.open(
                str(
                    self.audio_log_dir
                    / f"{self.get_participant_name(speaker_id)}_{speaker_id}.wav"
                ),
                "wb",
            )
            wave_file.setnchannels(1)
            wave_file.setsampwidth(2)
            wave_file.setframerate(sample_rate)
            self.audio_files[speaker_id] = wave_file
        self.audio_files[speaker_id].writeframes(b"".join([chunk]))

    def log_image(self, image, filename) -> Path:
        full_path = self.log_dir / filename
        image.save(full_path)
        return full_path
