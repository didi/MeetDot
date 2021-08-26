"""
base class for stream ASR services, like google stream ASR, didi stream ASR, etc.

Streaming ASR config setting
{
    session_id: XXX,
    encoding: the encoding scheme of the supplied audio,
    sample_rate_hertz: the sample rate (in Hertz) of the supplied audio,
    language_code: language code to use for speech recognition of the supplied audio,
    chunk_size: how much data(bytes) sending to ASR service each time,
}

API request
{
    session_id: unique ID for specific audio stream,
    data: "b'F\xfe\x88\xff\xe4\x00!\xfeB\xff<\xff4\x02\x8d\xffl\xff\xeb\x02H\x01\xdd'",
    end_utterance: Explicitly specify that the utterance should be ended now.
}

API response
{
    session_id: unique ID for specific audio stream,
    asr: speech recognition content,
    src_language: source language of speech recognition(e.g. “zh”, “en”),
    relative_time_offset: relative time offset of current ASR response
                           from the beginning of given audio stream,
    is_final:  True/False (True if current ASR text will not change anymore, else False)
}
"""

from .interface import SpeechRecognitionConfig, SpeechRecognitionRequest


class StreamAsr:
    def __init__(self, config: SpeechRecognitionConfig, logger, callback_fn):
        self.config = config
        self.user_language = config.language
        self.detected_language = config.language
        self.logger = logger
        self.callback_fn = callback_fn
        self.last_request: SpeechRecognitionRequest = SpeechRecognitionRequest(
            session_id="init", chunk=b""
        )

    def __call__(self, request: SpeechRecognitionRequest) -> None:
        raise NotImplementedError

    def terminate(self, wait_for_final=True):
        raise NotImplementedError

    def wait_for_final(self, timeout_seconds=1.0):
        raise NotImplementedError
