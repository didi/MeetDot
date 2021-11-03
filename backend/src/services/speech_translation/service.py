import functools
from dataclasses import replace
from typing import Any, Callable, Dict

from services.asr import (
    SpeechRecognitionRequest,
    SpeechRecognitionResponse,
    SpeechRecognitionService,
    LanguageIdRequest,
    LanguageIdResponse,
)
from services.post_asr import (
    PostASRRequest,
    PostASRResponse,
    PostASRService,
)
from services.captioning import (
    CaptioningRequest,
    CaptioningResponse,
    CaptioningService,
)
from services.post_translation import (
    PostTranslationRequest,
    PostTranslationResponse,
    PostTranslationService,
)
from services.translation import (
    TranslationRequest,
    TranslationResponse,
    TranslationService,
)
from services.types import ServiceRequest, ServiceResponse
from utils import start_thread

from .interface import SpeechTranslationRequest, TextTranslationRequest
from .session import Session


class SpeechTranslationService:
    def __init__(
        self, config, logger, languages, start_time, start_background_task=start_thread
    ):
        self.config = config
        self.logger = logger
        self.languages = languages  # target languages
        self.start_background_task = start_background_task
        self.start_time = start_time
        self.listeners = {
            "asr": [],
            "text": [],
            "language-update": [],
            "translation": [],
            "post-translation": [],
            "captioning": [],
        }
        self.sessions: Dict[str, Session] = {}

        # Initialize component services
        self.asr_service = SpeechRecognitionService
        self.post_asr_service = PostASRService(config.post_asr, logger=logger)
        self.mt_service = TranslationService(
            config=self.config.translation,
            callback_fn=self._on_translation,
            logger=logger,
        )
        self.post_translation_service = PostTranslationService(
            config.post_translation, logger=logger
        )
        self.captioning_service = CaptioningService(
            config.captioning,
            logger=logger,
            callback_fn=functools.partial(self._notify_listeners, topic="captioning"),
        )

    def add_listener(
        self,
        topic,
        listener: Callable[[ServiceRequest, ServiceResponse], Any],
    ):
        """
        Add a listener to a topic (transcript, translation,
        de-flickered translation, and captioning).
        """

        if topic not in self.listeners:
            raise ValueError(f"Could not add listener to topic {topic}")
        self.listeners[topic].append(listener)

    def start_listening(self, session_id, language):
        """
        Begin processing audio in language for session_id and producing
        transcripts and translations.
        """

        if session_id not in self.sessions:
            # Initialize asr service and start listening
            asr_config = replace(self.config.asr, language=language)
            asr_service = self.asr_service(
                config=asr_config,
                logger=self.logger,
                start_time=self.start_time,
                callback_fn=self._on_transcript,
                language_id_callback_fn=self._on_language_update,
            )
            recognizer_thread = self.start_background_task(target=asr_service.run)
            language_id_thread = self.start_background_task(
                target=asr_service.run_language_detect
            )
            self.sessions[session_id] = Session(
                session_id=session_id,
                language=language,
                asr_service=asr_service,
                recognizer_thread=recognizer_thread,
                language_id_thread=language_id_thread,
            )

    def stop_listening(self, session_id, wait_for_final=True):
        """
        Stop processing session session_id
        """

        session = self.sessions.get(session_id)

        if session is None:
            return

        # terminate active asr service for specific participant
        session = self.sessions[session_id]
        session.asr_service.terminate(wait_for_final=wait_for_final)

        if wait_for_final:
            session.recognizer_thread.join(timeout=10)
            session.language_id_thread.join()

        self.mt_service.end_session(session_id, wait_for_final)
        self.captioning_service.end_session(session_id)
        self.sessions.pop(session_id, None)

    def __call__(self, request: SpeechTranslationRequest) -> None:
        """
        Process a request, containing a session ID and a chunk of audio
        """

        session = self.sessions.get(request.session_id)

        if session is None:
            return

        session.asr_service(
            SpeechRecognitionRequest(
                request.session_id,
                request.chunk,
                request.end_utterance,
            )
        )

    def _on_transcript(
        self,
        asr_request: SpeechRecognitionRequest,
        asr_response: SpeechRecognitionResponse,
    ):
        """
        Broadcast new asr response to listeners, and translate
        """

        self._notify_listeners("asr", asr_request, asr_response)

        # Send ASR response to be translated
        session = self.sessions.get(asr_request.session_id)

        if session is None:
            return

        post_asr_request = PostASRRequest(
            transcript=asr_response.transcript, language=asr_response.language
        )

        self.logger.debug(
            f"sid: {asr_request.session_id}, "
            + f"message_id: {asr_response.utterance_start_time}, "
            + f"asr_response_transcript: {asr_response.transcript}, "
        )

        post_asr_response = self.post_asr_service(post_asr_request)

        self.logger.debug(
            f"sid: {asr_request.session_id}, "
            + f"message_id: {asr_response.utterance_start_time}, "
            + f"post_asr_response_transcript: {post_asr_response.transcript}"
        )

        for target_language in self.languages(asr_response.language):
            # call translation service
            mt_request = TranslationRequest(
                session_id=asr_request.session_id,
                message_id=asr_response.utterance_start_time,
                text=post_asr_response.transcript,
                source_language=asr_response.language,
                target_language=target_language,
                is_final=asr_response.is_final,
            )
            self.mt_service(mt_request)

    def on_text(self, text_request: TextTranslationRequest):
        self.logger.debug(f"sid: {text_request.session_id}, text: {text_request.text}")
        self._notify_listeners("text", text_request, None)

        for target_language in self.languages(text_request.source_language):
            # call translation service
            mt_request = TranslationRequest(
                session_id=text_request.session_id,
                message_id=text_request.start_time,
                text=text_request.text,
                source_language=text_request.source_language,
                target_language=target_language,
                is_final=True,
                is_chat=True,
            )
            self.mt_service(mt_request)

    def _on_language_update(
        self, language_request: LanguageIdRequest, language_response: LanguageIdResponse
    ):
        self._notify_listeners("language-update", language_request, language_response)
        self.logger.debug(
            f"sid: {language_request.session_id}, "
            f"language switch to {language_response.detected_language}"
        )

    def _on_translation(
        self, mt_request: TranslationRequest, mt_response: TranslationResponse
    ):
        # Notify listeners of translation
        self._notify_listeners("translation", mt_request, mt_response)

        self.logger.debug(
            f"sid: {mt_request.session_id}, translated {mt_request.source_language} "
            f"to {mt_request.target_language}, {mt_response.translation}"
        )

        # call post-translation service
        post_translation_request = PostTranslationRequest(
            session_id=mt_request.session_id,
            message_id=mt_request.message_id,
            translation=mt_response.translation,
            is_final=mt_request.is_final,
            original_language=mt_request.source_language,
            language=mt_request.target_language,
            is_chat=mt_request.is_chat,
        )
        post_translation_response = self.post_translation_service(
            post_translation_request
        )

        # Notify listeners of translation with post-processing applied
        self._notify_listeners(
            "post-translation", post_translation_request, post_translation_response
        )

        self.logger.debug(
            f"sid: {post_translation_request.session_id}, result after "
            f"post-translation: {post_translation_response.translation}"
        )

        # Call captioning service
        caption_request = CaptioningRequest(
            session_id=mt_request.session_id,
            message_id=mt_request.message_id,
            original_language=mt_request.source_language,
            target_language=mt_request.target_language,
            utterance=post_translation_response.translation,
            utterance_complete=mt_request.is_final,
        )
        self.captioning_service(caption_request)

    def _notify_listeners(self, topic, service_request, service_response):
        """
        Called when a new translation response is received (callback function)
        """

        session = self.sessions.get(service_request.session_id)

        if session is None:
            return

        for listener in self.listeners[topic]:
            listener(service_request, service_response)
