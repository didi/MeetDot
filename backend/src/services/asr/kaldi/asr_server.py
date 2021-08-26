import argparse
import asyncio
import concurrent.futures
import json
import logging
import os
import pathlib
import sys

import websockets
from services.asr.kaldi import KaldiStreamAsr
from vosk import KaldiRecognizer, Model


def process_chunk(rec, message):
    if message == '{"eof" : 1}':
        return rec.FinalResult(), True
    elif rec.AcceptWaveform(message):
        return rec.Result(), False
    else:
        return rec.PartialResult(), False


async def recognize(websocket, path):
    rec, model, sample_rate = None, None, None
    last_response = None

    while True:

        message = await websocket.recv()

        if isinstance(message, str) and "config" in message:
            # Load configuration if provided

            config = json.loads(message)["config"]

            sample_rate = config.get("sample_rate_hertz", 16000)
            language = config.get("language", "en-US")
            model = models[language]

            continue

        if not rec:
            assert (
                model is not None and sample_rate is not None
            ), "Need to send config as first message"
            rec = KaldiRecognizer(model, sample_rate)

        response, stop = await loop.run_in_executor(pool, process_chunk, rec, message)

        if response == last_response:
            # Don't resend repeated transcript

            continue

        last_response = response
        try:
            await websocket.send(response)
        except websockets.exceptions.ConnectionClosedOK:
            logging.info("Socket was closed before last message sent, handled")

        if stop:
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=2700)
    parser.add_argument("--models_dir", type=str, default="models")
    args = parser.parse_args()

    logger = logging.getLogger("websockets")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    # Gpu part, uncomment if vosk-api has gpu support
    #
    # from vosk import GpuInit, GpuInstantiate
    # GpuInit()
    # def thread_init():
    #     GpuInstantiate()
    # pool = concurrent.futures.ThreadPoolExecutor(initializer=thread_init)

    models = {
        language: Model(os.path.join(args.models_dir, language))
        for language in KaldiStreamAsr.SUPPORTED_LANGUAGES
    }
    logging.info(f"Loaded ASR models: {list(models.keys())}")
    pool = concurrent.futures.ThreadPoolExecutor((os.cpu_count() or 1))
    loop = asyncio.get_event_loop()

    start_server = websockets.serve(recognize, args.host, args.port)

    loop.run_until_complete(start_server)
    loop.run_forever()
