import collections.abc
import json
from pathlib import Path
import re
import threading
import time
from typing import List
import wave


def deep_update(d, u):
    """
    Deeply update elements of nested dict d with update u
    """

    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v

    return d


def start_thread(target, *args, **kwargs):
    """
    Starts a thread running the function target
    """
    thread = threading.Thread(target=target, args=args, kwargs=kwargs)
    thread.start()

    return thread


def get_duration_seconds(wav_path):
    """
    Given a .wav file, return the duration in seconds
    """
    with wave.open(wav_path) as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


def get_current_time_ms():
    """Return Current Time in MS."""

    return int(round(time.time() * 1000))


def sum_dict(a, b):
    """
    Sum the corresponding keys of numeric dictionaries a and b
    """

    if not a:
        return b

    if not b:
        return a

    return {k: a.get(k, 0) + b.get(k, 0) for k in a.keys() | b.keys()}


def remove_chinese_punctuation(s):
    punc = "！？｡。＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏."

    return re.sub(r"[%s]+" % punc, "", s)


def write_list_to_file(
    input_list: List,
    output_path: Path,
):
    with open(output_path, "w", encoding="utf-8", buffering=1) as f:
        for line in input_list:
            f.write(line + "\n")


def load_text_file(input_path):
    with open(input_path, encoding="utf-8") as f:
        lines = f.readlines()

    return [line.strip() for line in lines]


def load_json(input_path):
    with open(input_path, encoding="utf-8") as f:
        return json.load(f)


class ThreadSafeDict(dict):
    """Thread-safe usage:
    u = ThreadSafeDict()
    # Everything under 'with' is atomic.
    with u as m:
        m[1] = 'foo'
    """

    def __init__(self, *p_arg, **n_arg):
        dict.__init__(self, *p_arg, **n_arg)
        self._lock = threading.Lock()

    def __enter__(self):
        self._lock.acquire()

        return self

    def __exit__(self, type, value, traceback):
        self._lock.release()


def safe_divide(a, b):
    if b == 0:
        return 0
    else:
        return a / b
