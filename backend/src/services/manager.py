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

from collections import defaultdict
import re
import time
from typing import List, Tuple

from flask import escape

from .asr import (
    SpeechRecognitionRequest,
    SpeechRecognitionResponse,
    LanguageIdRequest,
    LanguageIdResponse,
)
from .captioning import CaptioningRequest, CaptioningResponse
from .image_translation import ImageTranslationService, ImageTranslationRequest
from .post_translation import PostTranslationRequest, PostTranslationResponse
from .speech_translation import (
    SpeechTranslationRequest,
    TextTranslationRequest,
    SpeechTranslationService,
)
from .utterance import CompletedUtterance


class Manager:
    def __init__(self, room, socket):
        self.room = room
        self.socket = socket
        self.completed_utterances = {}
        self.start_time = time.time()
        self.speech_translator = SpeechTranslationService(
            config=room.settings.st_services,
            logger=self.room.logger,
            languages=lambda utterance_lang: self.room.caption_languages()
            | {utterance_lang},
            start_background_task=self.socket.start_background_task,
            start_time=self.start_time,
        )
        self.image_translator = ImageTranslationService(
            config=room.settings.img_services,
            logger=self.room.logger,
        )

        self.add_transcript_listener(self._broadcast_transcript)
        self.add_language_update_listener(self._broadcast_language_detection_update)
        self.add_caption_listener(self._broadcast_captions)
        self.add_text_listener(self.save_text_history)
        self.add_post_translation_listener(self._broadcast_utterances)
        self.add_post_translation_listener(self._broadcast_complete_utterances)
        self.add_post_translation_listener(self.log_utterance)

        # message history in the original spoken language.
        self.transcript: List[
            Tuple[SpeechRecognitionRequest, SpeechRecognitionResponse]
        ] = []
        self.chat_history: List[TextTranslationRequest] = []

        # language -> list of utterances
        self.translations = defaultdict(list)

        # maps message_id -> dict of reactions (e.g. {'user': '😄'})
        self.reactions = defaultdict(dict)

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

    async def on_image_data(self, session_id, source_language, target_language, image):
        request = ImageTranslationRequest(
            session_id=session_id,
            source_language=source_language,
            target_language=target_language,
            source_image=image,
        )
        return await self.image_translator.call(request)

    def on_text_data(self, session_id, message, source_language):
        request = TextTranslationRequest(
            session_id=session_id,
            source_language=source_language,
            text=message,
            start_time=time.time() - self.start_time,
        )
        self.speech_translator.on_text(request)

    def add_participant(self, session_id, participant):
        self.speech_translator.start_listening(session_id, participant.spoken_language)
        self.add_new_languages(participant.caption_languages)

    def remove_participant(self, session_id):
        self.speech_translator.stop_listening(session_id, wait_for_final=False)

    def update_spoken_language(self, session_id, spoken_language):
        if self.speech_translator.config.asr.middleware_provider is None:
            self.speech_translator.stop_listening(session_id, wait_for_final=False)
            self.speech_translator.start_listening(session_id, spoken_language)
        else:
            self.speech_translator.sessions[session_id].language = spoken_language
            self.speech_translator.sessions[session_id].asr_service.accept_new_language(
                spoken_language
            )

    def add_new_languages(self, languages):
        """Translate all messages in history"""

        # TODO: Use a TranslationService instead of a SpeechTranslationService
        # for more control and to eliminate possible bugs.

        new_languages = set(languages) - set(self.room.caption_languages())
        if not new_languages:
            return

        # Create a new speech translator instance without any listeners
        # except populating the history panel to avoid triggering other processes
        catchup_speech_translator = SpeechTranslationService(
            config=self.room.settings.st_services,
            logger=self.room.logger,
            languages=lambda _: new_languages,
            start_background_task=self.socket.start_background_task,
            start_time=self.start_time,
        )

        catchup_speech_translator.sessions = self.speech_translator.sessions
        catchup_speech_translator.add_listener(
            "post-translation", self._wrap_listener(self._broadcast_complete_utterances)
        )

        new_lang = new_languages.pop() if len(new_languages) == 1 else None

        for request, response in self.transcript:

            # Don't translate into original language. This doesn't work if multiple languages
            # are added at once, but can change when using TranslationService individually
            if response.language == new_lang:
                continue

            catchup_speech_translator._on_transcript(request, response)
            time.sleep(0.05)

            # TODO: Space out these translation requests on low priority
            # Running messages throught the translator comes with a bunch of problems.
            # Combining messages assumes everything will be in order, and the translator
            # rate limits may cause messages to be dropped.

        for req in self.chat_history:
            catchup_speech_translator.on_text(req)

    def add_transcript_listener(self, fn):
        self.speech_translator.add_listener("asr", self._wrap_listener(fn))

    def add_text_listener(self, fn):
        self.speech_translator.add_listener("text", self._wrap_listener(fn))

    def add_language_update_listener(self, fn):
        self.speech_translator.add_listener("language-update", self._wrap_listener(fn))

    def add_translation_listener(self, fn):
        self.speech_translator.add_listener("translation", self._wrap_listener(fn))

    def add_post_translation_listener(self, fn):
        self.speech_translator.add_listener("post-translation", self._wrap_listener(fn))

    def add_caption_listener(self, fn):
        self.speech_translator.add_listener("captioning", self._wrap_listener(fn))

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
                f"/{request.target_language}/translation",
                {
                    "speaker_id": request.session_id,
                    "message_id": request.message_id,
                    "translation_lines": response.lines,
                    "line_index": response.line_index,
                    "highlight_boundaries": response.highlight_boundaries,
                    "original_language": request.original_language,
                },
                room=room_id,
                broadcast=True,
            )

    def save_text_history(self, request: TextTranslationRequest, _unused, room_id: str):
        self.chat_history.append(request)

    def _broadcast_utterances(
        self,
        request: PostTranslationRequest,
        response: PostTranslationResponse,
        room_id: str,
    ):
        speaker = self.room.participants.get(request.session_id)
        utterance = {
            "speaker_id": request.session_id,
            "speaker_name": speaker.name,
            "speaker_language": speaker.spoken_language,
            "message_id": request.message_id,
            "text": response.translation,
        }
        self.socket.emit(
            f"/{request.language}/utterance",
            utterance,
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
            "speaker_language": request.original_language,
            "language": request.language,
            # WARNING! This is rendered directly by the browser.
            # It must be sanitized to remove XSS risks, e.g. scripts
            "html": self.render_url_and_sanitize(response.translation),
            "text": response.translation,
            "reactions": {},  # new messages have no reactions. they will be added later.
            "timestamp": time.time(),  # used by summarizer to count the speaking time
        }

        # Combine consective utterances in translations
        if not self.translations[request.language]:
            self.translations[request.language].append(utterance)
        else:
            last_utterance = self.translations[request.language][-1]

            # Bug: The catchup translator creates duplicate utterances, but I can't
            # figure it out rn. Catch some of these and skip them
            if last_utterance["message_id"] == utterance["message_id"]:
                return

            if (
                last_utterance["speaker_name"] == utterance["speaker_name"]
                and last_utterance["speaker_language"] == utterance["speaker_language"]
                and not request.is_chat
            ):

                last_utterance["html"] = last_utterance["html"] + utterance["html"]
                last_utterance["text"] = last_utterance["text"] + utterance["text"]

                utterance = last_utterance
            else:
                # Insert the new utterance into history.
                # "insert or sort" is a simple method with reasonably good performance.
                self.translations[request.language].append(utterance)
                if last_utterance["message_id"] > utterance["message_id"]:
                    # TimSort is good if the array is almost in order
                    self.translations[request.language].sort(
                        key=lambda u: u["message_id"]
                    )

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

    def render_url_and_sanitize(self, text):
        """
        Convert HTML to links and sanitize it. Do this in one step to prevent
        accidental XSS vulnerabilities
        """
        URL_REGEX = (
            r"((https?:\/\/)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]"
            r"{1,6}\b([-a-zA-Z0-9()@:;%_\+.~#?&//=]*))"
        )

        def create_hyperlinks(match):
            url = match.group(1)

            if not url.startswith("http"):
                target_url = "http://" + url
            else:
                target_url = url

            return f"""<a href="{target_url}" rel="noopener noreferrer" target="_blank">
                {url[:100]}{"..." if len(url) > 100 else ""}
            </a>"""

        text = escape(text)
        return re.sub(URL_REGEX, create_hyperlinks, text)
