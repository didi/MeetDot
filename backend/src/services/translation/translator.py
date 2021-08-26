"""

base class for different translation service, like didi MT, google MT, etc.
"""
import threading
import time
from threading import Condition

import gevent

from utils import ThreadSafeDict

from .interface import TranslationConfig, TranslationRequest, TranslationResponse


# TODO(scotfang): Maybe make TranslationEventLoop time out after period of inactivity.
class TranslationEventLoop:
    def __init__(
        self, session_id, min_interval_ms, min_interval_char, translation_fn, logger
    ):
        self.session_id = session_id
        self.min_interval_ms = min_interval_ms
        self.min_interval_char = min_interval_char
        self.translation_fn = translation_fn
        self.logger = logger

        self.latest_request = None
        self.latest_completed_request_text = ""
        self.condition = Condition()
        self.exit_loop = False
        self.loop_thread = threading.Thread(target=self.loop)

    def start(self):
        self.loop_thread.start()

    def ready(self):
        return (
            self.latest_request is not None
            and (
                self.latest_request.is_final
                or len(self.latest_request.text)
                - len(self.latest_completed_request_text)
                >= self.min_interval_char
            )
        ) or self.exit_loop

    def loop(self):
        while True:
            with self.condition:
                self.condition.wait_for(self.ready)
                request = self.latest_request

                if request:
                    self.latest_request = None

                    if not request.is_final:
                        self.latest_completed_request_text = request.text
                    else:
                        assert self.latest_completed_request_text == ""

                exit_loop = self.exit_loop

            if request:
                start_time_ns = time.time_ns()
                self.translation_fn(request)
                time_elapsed_ns = time.time_ns() - start_time_ns

                if not exit_loop:
                    sleep_time_s = (
                        self.min_interval_ms - time_elapsed_ns / 1e6
                    ) / float(1e3)

                    if sleep_time_s > 0:
                        time.sleep(sleep_time_s)

            if exit_loop:
                break


class Translator:
    def __init__(
        self,
        config: TranslationConfig,
        callback_fn,
        logger,
        start_background_task,
    ):
        self.config = config
        self.callback_fn = callback_fn
        self.logger = logger
        self.start_background_task = start_background_task

        # session_key -> TranslationEventLoop
        self.session_event_loops = ThreadSafeDict()
        # TODO(scotfang) make previous_translations garbage collect stale sessions
        # session_key -> previous_translation
        self.previous_translations = ThreadSafeDict()

    def __call__(self, request: TranslationRequest):
        session_key = request.session_key()
        # Retrieve previous_translation for biased_decoding, and also
        # clear the previous_translation for a given session if the
        # request is final.

        if not request.previous_translation or request.is_final:
            with self.previous_translations as pt:
                if not request.previous_translation:
                    prev_translation = pt.get(session_key)

                    if prev_translation:
                        request.previous_translation = prev_translation

                if request.is_final and session_key in pt:
                    del pt[session_key]

        if session_key not in self.session_event_loops:
            new_event_loop = TranslationEventLoop(
                session_key,
                self.config.min_interval_ms,
                self.config.min_interval_char,
                self.call_translate,
                self.logger,
            )
            new_event_loop.start()
            with self.session_event_loops as event_loops:
                event_loops[session_key] = new_event_loop

        event_loop = self.session_event_loops[session_key]
        with event_loop.condition:
            event_loop.latest_request = request

            if request.is_final:
                event_loop.latest_completed_request_text = ""
            event_loop.condition.notify()

    def call_translate(self, request):
        translation, raw_translation = self.translate(request)
        response = TranslationResponse(
            translation=translation, raw_translation=raw_translation
        )

        if not request.is_final:
            with self.previous_translations as pt:
                pt[request.session_key()] = (
                    response.raw_translation
                    if response.raw_translation
                    else response.translation
                )
                # TODO(scotfang): Perhaps move this to after captioning, since we don't need to bias
                #                 towards anything the user hasn't seen.  However, for now we only
                #                 do biased-decoding with response.raw_translation, which isn't
                #                 affected by anti-flicker or captioning.

        self.callback_fn(request, response)

    def end_session(self, target_session_id, wait_for_final=True):
        keys_to_delete = []
        finished_event_loops = []

        with self.session_event_loops as event_loops:
            for session_key, loop in event_loops.items():
                session_id, _, _ = session_key

                if session_id == target_session_id:
                    keys_to_delete.append(session_key)
                    finished_event_loops.append(loop)

        for loop in finished_event_loops:
            with loop.condition:
                loop.exit_loop = True
                loop.condition.notify()

            if wait_for_final:
                loop.loop_thread.join()

        with self.session_event_loops as event_loops:
            for k in keys_to_delete:
                del event_loops[k]

        keys_to_delete = []
        # NOTE: If wait_for_final=False, it's possible that keys we want to
        #       delete will be added by event loops after this deletion loop.
        #       That's why there's a TODO to garbage collect stale entries.
        with self.previous_translations as pt:
            for k in pt:
                session_id = k[0]

                if session_id == target_session_id:
                    keys_to_delete.append(k)

            for k in keys_to_delete:
                del pt[k]

    def translate(self, request: TranslationRequest):
        """Should return translation and raw_translation"""
        raise NotImplementedError
