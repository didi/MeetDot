"""
Google cloud stream ASR service class (using Python client library)
"""
import logging
import queue
import time
from datetime import datetime
from threading import Timer

import gevent
from google.api_core import exceptions
from google.cloud import speech
from google.cloud.speech import enums, types
from utils import get_current_time_ms

from .interface import SpeechRecognitionRequest, SpeechRecognitionResponse
from .resumable_microphone_stream import ResumableMicrophoneStream
from .stream_asr import StreamAsr


class GoogleStreamAsr(StreamAsr):
    SUPPORTED_LANGUAGES = ("en-US", "zh", "pt-BR", "es-ES")

    def __init__(self, config, logger, start_time, callback_fn):
        super().__init__(config, logger, start_time, callback_fn)
        self.listening = False

        if not self.config.encoding:
            # Set encoding as default
            self.config.encoding = speech.enums.RecognitionConfig.AudioEncoding.LINEAR16

        self._google_stream_asr_config_setting()

        # if ASR hasn't changed for N seconds, but no IsFinal, exit listen_asr_loop()

        if self.config.language != "en-US":
            self.max_silence_time = 2  # second
            self.logger.debug(
                f"set max_silence_time for {self.config.language} "
                + f"to {self.max_silence_time} seconds"
            )
            self.silence_timer = RepeatedTimer(1.0, self._check_max_silence_time)
        else:
            self.silence_timer = None

        self.last_response_time = None

    def _google_stream_asr_config_setting(self):
        self.stream_limit = 240000
        # if want more detailed log for debugging, set log_level to "INFO" or "DEBUG"

        self.logger.info(f"Google Stream ASR config setting: {self.config}")

        self.asr_service_config(
            sample_rate=self.config.sample_rate_hertz,
            lang_code=self.config.language,
            chunk_size=self.config.chunk_size,
        )

    def asr_service_config(self, sample_rate, lang_code, chunk_size):
        """
        initialize ASR service, currently only support GOOGLE ASR SDK;
        """

        self.google_speech_client = speech.SpeechClient()
        self.google_asr_config = speech.types.RecognitionConfig(
            encoding=self.config.encoding,
            sample_rate_hertz=sample_rate,
            language_code=lang_code,
            max_alternatives=1,
        )
        self.streaming_config = speech.types.StreamingRecognitionConfig(
            config=self.google_asr_config, single_utterance=False, interim_results=True
        )
        self.mic_stream = ResumableMicrophoneStream(
            sample_rate,
            chunk_size,
        )

    def run(self):
        """start streaming from microphone input to speech API"""
        with self.mic_stream as stream:
            while not stream.closed:
                # audio stream segment is subject to stream_limit setting
                self.logger.info(
                    "Speaker started streaming speech recognition"
                    + f" (number {stream.restart_counter})"
                )
                stream.audio_input = []

                # Stream is paused or otherwise interrupted. Block until data is received

                audio_generator = stream.generator()
                requests = (
                    speech.types.StreamingRecognizeRequest(audio_content=chunk)
                    for chunk in audio_generator
                )

                """
                We set stream limit (e.g. 4mins) to make sure streaming_recognize() does not
                timeout in an unexpected way.
                We periodically break out of listen_asr_loop, and call streaming_recognize() again.
                # google could API documentation:
                # https://googleapis.dev/python/speech/latest/_modules/google/cloud/speech_v1/services/speech/client.html#SpeechClient.streaming_recognize
                """
                self.listening = True
                try:
                    responses = self.google_speech_client.streaming_recognize(
                        self.streaming_config, requests
                    )
                except (
                    exceptions.OutOfRange,
                    exceptions.Cancelled,
                    exceptions.ServiceUnavailable,
                ) as e:
                    self.logger.error("Google API error: %s", e)

                    break
                except ValueError:
                    # Channel has been closed, stopped listening

                    break

                self.listen_asr_loop(responses, stream)
                self.listening = False

                if stream.result_end_time > 0:
                    stream.final_request_end_time = stream.is_final_end_time
                stream.result_end_time = 0
                stream.last_audio_input = stream.audio_input
                stream.audio_input = []
                stream.restart_counter = stream.restart_counter + 1
                stream.new_stream = True

    def _check_max_silence_time(self):
        if (
            self.last_response_time
            and abs(time.time() - self.last_response_time) > self.max_silence_time
        ):
            self.logger.debug("max_silence_time reached")
            self.mic_stream.fill_buffer(None)

    def listen_asr_loop(self, responses, stream):
        """Iterates through server responses and prints them.

        The responses passed is a generator that will block until a response
        is provided by the server.

        Each response may contain multiple results, and each result may contain
        multiple alternatives; for details, see https://goo.gl/tjCPAU.  Here we
        print only the transcription for the top alternative of the top result.

        In this case, responses are provided for interim results as well. If the
        response is an interim one, print a line feed at the end of it, to allow
        the next result to overwrite it, until the response is a final one. For the
        final one, print a newline to preserve the finalized transcription.
        """
        self.last_response_time = None
        transcript, last_transcript = "", ""

        while True:
            try:
                response = next(responses)
            except StopIteration:
                return
            except exceptions.OutOfRange as e:
                self.logger.error("Google API error: %s", e)

                break
            except (exceptions.Cancelled, exceptions.ServiceUnavailable):
                # Channel has been closed, stopped listening

                break

            if not response.results:
                continue

            result = response.results[0]

            if result.stability and result.stability < self.config.stability_threshold:
                continue

            if not result.alternatives:
                continue

            result_time_ms = 0

            if result.result_end_time.seconds:
                result_time_ms += result.result_end_time.seconds * 1000

            if result.result_end_time.nanos:
                result_time_ms += result.result_end_time.nanos / 1000000

            stream.result_end_time = result_time_ms
            self.last_response_time = time.time()
            # total stream duration (consider stream restarts multiple times)
            # in milliseconds
            transcript = result.alternatives[0].transcript

            if transcript == last_transcript and not result.is_final:
                continue

            last_transcript = transcript

            self.logger.debug(f"Utterance recognized by ASR: {transcript}")
            current_time = time.time()

            if self.utterance_start_time is None:
                self.utterance_start_time = current_time - self.start_time
            response = SpeechRecognitionResponse(
                transcript=transcript,
                utterance_start_time=self.utterance_start_time,
                utterance_length=current_time - self.utterance_start_time,
                is_final=result.is_final,
                language=self.config.language,
            )
            if result.is_final:
                # Reset the start time at the end of the utterance
                self.utterance_start_time = None

            stream_time_limit_exceed_flag = (
                get_current_time_ms() - stream.start_time
            ) > self.stream_limit

            if stream_time_limit_exceed_flag:
                # Restart stream if time exceeded
                stream.start_time = get_current_time_ms()
                break

            # Broadcast response_data to listeners
            self.callback_fn(self.last_request, response)

        if len(transcript.strip()) > 0:
            # Send final response
            current_time = time.time()
            if self.utterance_start_time is None:
                self.utterance_start_time = current_time - self.start_time
            response = SpeechRecognitionResponse(
                transcript=transcript,
                utterance_start_time=self.utterance_start_time,
                utterance_length=current_time - self.utterance_start_time,
                is_final=True,
                language=self.config.language,
            )
            self.callback_fn(self.last_request, response)

    def __call__(self, request: SpeechRecognitionRequest):
        self.last_request = request
        self.mic_stream.fill_buffer(request.chunk)

    def close_audio_stream(self):
        # close the active ResumableMicrophoneStream instance
        self.mic_stream.closed = True

    def end_utterance(self):
        self.mic_stream.__exit__(None, None, None)

        if self.silence_timer:
            self.silence_timer.stop()

    def terminate(self, wait_for_final=True):
        self.end_utterance()

        if wait_for_final:
            self.wait_for_final()
        self.google_speech_client.transport.channel.close()

    def wait_for_final(self, timeout_seconds=2.0):
        """
        After closing, wait until the final response is sent, up to a timeout
        """
        q = queue.Queue()
        original_callback = self.callback_fn

        def wrapped_callback(request, response):
            if response.is_final:
                q.put(response)
            original_callback(request, response)

        self.callback_fn = wrapped_callback
        try:
            final_response = q.get(timeout=timeout_seconds)
        except queue.Empty:
            final_response = SpeechRecognitionResponse(
                transcript="",
                utterance_start_time=0,
                is_final=True,
                language=self.config.language,
            )
        self.callback_fn = original_callback

        while self.listening:
            gevent.sleep(0.01)

        return final_response


class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False
