from .interface import (
    SpeechRecognitionConfig,
    SpeechRecognitionRequest,
    SpeechRecognitionResponse,
    LanguageIdRequest,
    LanguageIdResponse,
)
from .service import SpeechRecognitionService

import os
import urllib.request
import tarfile
import warnings

try:
    from .kaldi_stream_asr import PRETRAINED_MODEL_DIR
except ModuleNotFoundError:
    warnings.warn("Warning: Kaldi not installed", ImportWarning)
    PRETRAINED_MODEL_DIR = None


def download_model(model_name):
    """Download kaldi models"""
    model_path = os.path.join(PRETRAINED_MODEL_DIR, model_name)
    if os.path.exists(model_path):
        return

    print("Downloading Kaldi {} model...".format(model_name))
    url = "http://172.21.144.71/~boliangzhang/kaldi_pretrained_model/{}.tar.gz".format(
        model_name
    )
    dest = "{}/{}.tar.gz".format(PRETRAINED_MODEL_DIR, model_name)
    urllib.request.urlretrieve(url, dest)

    print("Extracting Kaldi {} model...".format(model_name))

    tar_path = "{}.tar.gz".format(os.path.join(PRETRAINED_MODEL_DIR, model_name))
    dest = PRETRAINED_MODEL_DIR
    tar = tarfile.open(tar_path)
    tar.extractall(dest)
    tar.close()

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            "Fail to download {} pretrained model. Model {} not found.".format(
                model_name, model_path
            )
        )


# configure model paths (hard-coded for now, will change later)
if PRETRAINED_MODEL_DIR:
    os.makedirs(PRETRAINED_MODEL_DIR, exist_ok=True)
    # download EN asr model
    download_model("en.aspire")
    # download ZH asr model
    download_model("zh.multi_cn")
