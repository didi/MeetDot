import json
import logging
import re
import sys
import wave

from six.moves import queue

from utils import get_current_time_ms


class ResumableMicrophoneStream:
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(
        self,
        sample_rate,
        chunk_size,
        stream_limit=24000,
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.stream_limit = stream_limit
        self._num_channels = 1
        self._buff = queue.Queue()
        self.closed = True
        self.start_time = get_current_time_ms()
        self.restart_counter = 0
        self.audio_input = []
        self.last_audio_input = []
        self.result_end_time = 0
        self.is_final_end_time = 0
        self.final_request_end_time = 0
        self.bridging_offset = 0
        self.last_transcript_was_final = False
        self.new_stream = True

    def __enter__(self):
        """
        Called at the beginning of a 'with' statement
        """
        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        """
        Called at the end of a 'with' statement
        """

        if self.closed:
            return

        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)

    def fill_buffer(self, in_data, *args, **kwargs):
        """
        Args:
            in_data: bytes format

        Continuously collect data from the audio stream, into the buffer.

        in_data example(partial):
            b'F\xfe\x88\xff\xe4\x00!\xfeB\xff<\xff4\x02\x8d\xffl\xff\xeb\x02H\x01\xdd'
        """
        self._buff.put(in_data)

    def generator(self):
        """Stream Audio from microphone to API and to local buffer"""

        while not self.closed:
            if self.new_stream and self.last_audio_input:

                chunk_time = self.stream_limit / len(self.last_audio_input)

                if chunk_time != 0:

                    if self.bridging_offset < 0:
                        self.bridging_offset = 0

                    if self.bridging_offset > self.final_request_end_time:
                        self.bridging_offset = self.final_request_end_time

                    chunks_from_ms = round(
                        (self.final_request_end_time - self.bridging_offset)
                        / chunk_time
                    )

                    self.bridging_offset = round(
                        (len(self.last_audio_input) - chunks_from_ms) * chunk_time
                    )

                self.new_stream = False

            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            self.audio_input.append(chunk)

            if chunk is None:

                return
            yield chunk
            # Now consume whatever other data's still buffered.

            while True:
                try:
                    chunk = self._buff.get(block=False)

                    if chunk is None:
                        return
                    yield chunk
                    self.audio_input.append(chunk)
                except queue.Empty:
                    break
