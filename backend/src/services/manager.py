"""
Manager class is to manage audio streams from multiple users in a single room.
There is one manager instance per room.
The main responsibilites of Manager class are:

1) initialize services (e.g. ASR, MT, post-translation, captioning)
2) take incoming audio data requests from diffrent speakers in the same room,
3) manage intermediate API calls in the room
4) send corresponding captioning lines to speakers
    (different language speakers get different language captioning lines)
"""

import os
from collections import Counter, defaultdict
from textwrap import dedent
import time

from .asr import (
    SpeechRecognitionRequest,
    SpeechRecognitionResponse,
    LanguageIdRequest,
    LanguageIdResponse,
)
from .captioning import CaptioningRequest, CaptioningResponse
from .post_translation import PostTranslationRequest, PostTranslationResponse
from .speech_translation import (
    SpeechTranslationConfig,
    SpeechTranslationRequest,
    SpeechTranslationService,
)
from .utterance import CompletedUtterance


class Manager:
    def __init__(self, room, socket):
        self.room = room
        self.socket = socket
        self.completed_utterances = {}
        self.speech_translator = SpeechTranslationService(
            config=room.settings.services,
            logger=self.room.logger,
            languages=self.room.caption_languages,
            start_background_task=self.socket.start_background_task,
        )

        self.add_transcript_listener(self._broadcast_transcript)
        self.add_language_update_listener(self._broadcast_language_detection_update)
        self.add_caption_listener(self._broadcast_captions)
        self.add_post_translation_listener(self._broadcast_complete_utterances)
        self.add_post_translation_listener(self.log_utterance)

        # message history in the original spoken language.
        # list of tuples of (SpeechRecognitionRequest, SpeechRecognitionResponse)
        self.transcript = []
        self.translations = defaultdict(list)  # language -> list of utterances
        self.reactions = defaultdict(
            dict
        )  # message_id -> dict of reactions (e.g. {'user': '😄'})

    def on_audio_data(self, session_id, chunk, end_utterance=False):
        """
        receive audio chunk, and send it to corresponding stream ASR service.
        """

        if session_id not in self.speech_translator.sessions:
            return

        if self.room.settings.save_audio_logs:
            self.room.logger.log_audio_chunk(session_id, chunk)

        request = SpeechTranslationRequest(
            session_id=session_id, chunk=chunk, end_utterance=end_utterance
        )
        self.speech_translator(request)

    def add_participant(self, session_id, spoken_language, caption_language):
        self.speech_translator.start_listening(session_id, spoken_language)
        self.add_new_language(caption_language)

    def remove_participant(self, session_id):
        self.speech_translator.stop_listening(session_id, wait_for_final=False)

    def update_spoken_language(self, session_id, spoken_language):
        self.speech_translator.stop_listening(session_id, wait_for_final=False)
        self.speech_translator.start_listening(session_id, spoken_language)

    def add_new_language(self, lang: str):
        """Translate all messages in history"""
        if lang in self.room.caption_languages():
            return

        # Create a new speech translator instance without any listeners
        # except populating the history panel to avoid triggering other processes
        catchup_speech_translator = SpeechTranslationService(
            config=self.room.settings.services,
            logger=self.room.logger,
            languages=lambda: [lang],
            start_background_task=self.socket.start_background_task,
        )
        catchup_speech_translator.sessions = self.speech_translator.sessions
        catchup_speech_translator.add_listener(
            "post-translation", self._wrap_listener(self._broadcast_complete_utterances)
        )

        for request, response in self.transcript:
            catchup_speech_translator._on_transcript(request, response)

    def add_transcript_listener(self, fn):
        self.speech_translator.add_listener("asr", self._wrap_listener(fn))

    def add_language_update_listener(self, fn):
        self.speech_translator.add_listener("language-update", self._wrap_listener(fn))

    def add_translation_listener(self, fn):
        self.speech_translator.add_listener("translation", self._wrap_listener(fn))

    def add_post_translation_listener(self, fn):
        self.speech_translator.add_listener("post-translation", self._wrap_listener(fn))

    def add_caption_listener(self, fn):
        self.speech_translator.add_listener("captioning", self._wrap_listener(fn))

    def prepare_transcript(self, lang: str) -> str:
        result = []

        utterances = {msg["message_id"]: msg for msg in self.translations[lang]}
        for asr_request, asr_response in self.transcript:
            message_id = asr_response.relative_time_offset

            # Some messages aren't appearing in the translation.
            # This needs more debugging to find out why,
            # but this fixes the transcript panel for now
            if message_id not in utterances:
                continue

            utterance = utterances[message_id]
            result += f"{utterance['speaker_name']} ({lang}): {utterance['text']}\n"
            if utterance["speaker_language"] != lang:
                result += (
                    f"({utterance['speaker_language']}): {asr_response.transcript}\n"
                )
            if message_id in self.reactions:
                result += (
                    ", ".join(
                        f"{reaction}: {count}"
                        for reaction, count in Counter(
                            self.reactions[message_id].values()
                        ).most_common()
                    )
                    + "\n"
                )
            result += "\n"

        return result

    def _wrap_listener(self, fn):
        """
        Add the room_id to the listener's input
        """

        def wrapped_listener(*args, **kwargs):
            return fn(*args, **kwargs, room_id=self.room.room_id)

        return wrapped_listener

    def _broadcast_transcript(
        self,
        request: SpeechRecognitionRequest,
        response: SpeechRecognitionResponse,
        room_id: str,
    ):

        if response.transcript:
            self.socket.emit(
                "/transcript",
                {
                    "speaker_id": request.session_id,
                    "transcript": response.transcript,
                    "is_final": response.is_final,
                },
                room=room_id,
                broadcast=True,
            )
            if response.is_final:
                self.transcript.append((request, response))

    def _broadcast_captions(
        self,
        request: CaptioningRequest,
        response: CaptioningResponse,
        room_id: str,
    ):
        if response.lines and len(response.lines) > 0:
            self.socket.emit(
                f"/{request.language}/translation",
                {
                    "speaker_id": request.session_id,
                    "translation_lines": response.lines,
                    "line_index": response.line_index,
                    "highlight_boundaries": response.highlight_boundaries,
                },
                room=room_id,
                broadcast=True,
            )

    def _broadcast_complete_utterances(
        self,
        request: PostTranslationRequest,
        response: PostTranslationResponse,
        room_id: str,
    ):
        """
        Publish completed utterances, to be displayed in the full
        history panel
        """
        if not request.is_final:
            return

        speaker = self.room.participants.get(request.session_id)

        if speaker is None:
            return
        utterance = {
            "speaker_id": request.session_id,
            "message_id": request.message_id,
            "speaker_name": speaker.name,
            "speaker_language": speaker.spoken_language,
            "text": response.translation,
            "reactions": {},  # new messages have no reactions. they will be added later.
            "timestamp": time.time(),
        }
        self.translations[request.language].append(utterance)
        self.socket.emit(
            f"/{request.language}/complete-utterance",
            utterance,
            room=room_id,
            broadcast=True,
        )

    def _broadcast_language_detection_update(
        self,
        request: LanguageIdRequest,
        response: LanguageIdResponse,
        room_id: str,
    ):
        self.socket.emit(
            "/update-language",
            {
                "session_id": request.session_id,
                "detected_language": response.detected_language,
            },
            room=room_id,
        )

    def log_utterance(
        self,
        request: PostTranslationRequest,
        response: PostTranslationResponse,
        room_id: str,
    ):
        if not request.is_final:
            return

        if request.message_id in self.completed_utterances:
            self.completed_utterances[request.message_id].translations.append(
                (request.language, response.translation)
            )
        else:
            utterance = CompletedUtterance(
                message_id=request.message_id,
                speaker_name=self.room.participant_name(request.session_id),
                language=request.original_language,
                utterance=request.translation,
                translations=[],
            )
            self.completed_utterances[request.message_id] = utterance

        utterance = self.completed_utterances[request.message_id]
        if len(utterance.translations) + 1 >= len(self.room.caption_languages()):
            # TODO: Won't log an utterance if a new language joins part-way through.
            #       That should be rare though

            # If all translations have been collected, log the utterance
            self.room.logger.log_utterance(
                utterance.speaker_name,
                utterance.language,
                utterance.utterance,
                utterance.translations,
            )

            # Clean up
            self.completed_utterances.pop(request.message_id)
