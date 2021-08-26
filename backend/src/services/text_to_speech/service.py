import argparse
import sys

from pathlib import Path

from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    if v.lower() in ("no", "false", "f", "n", "0"):
        return False
    raise argparse.ArgumentTypeError("Boolean value expected.")


class TextToSpeechService:
    def __init__(
        self,
        language="en-US",
        model_name=None,
        config_path=None,
        vocoder_name=None,
        model_path=None,
        vocoder_path=None,
        vocoder_config_path=None,
        encoder_path=None,
        encoder_config_path=None,
    ):
        MODEL_NAMES = {
            "en-US": "tts_models/en/ljspeech/tacotron2-DDC",
            "es-ES": "tts_models/es/mai/tacotron2-DDC",
            "zh": "tts_models/zh-CN/baker/tacotron2-DDC-GST",
        }

        self.language = language
        if self.language not in MODEL_NAMES:
            print(
                "Error: current TTS service only support: {}".format(MODEL_NAMES.keys())
            )
            return

        self.model_name = MODEL_NAMES[language]
        self.model_path = model_path
        self.config_path = config_path
        self.vocoder_name = (
            "vocoder_models/universal/libri-tts/fullband-melgan"
            if self.language == "zh"
            else vocoder_name
        )
        self.vocoder_path = vocoder_path
        self.vocoder_config_path = vocoder_config_path
        self.encoder_path = encoder_path
        self.encoder_config_path = encoder_config_path

        self.use_cuda = False
        self.speakers_file_path = None
        self.speaker_idx = None
        self.speaker_wav = None
        self.gst_style = None
        self.list_models = None
        self.list_speaker_idxs = False
        self.save_spectogram = False

        # load model manager
        path = Path(__file__).parent / "models/.models.json"
        self.manager = ModelManager(path)
        self.load_models()

        # load tts model
        self.synthesizer = Synthesizer(
            self.model_path,
            self.config_path,
            self.speakers_file_path,
            self.vocoder_path,
            self.vocoder_config_path,
            self.encoder_path,
            self.encoder_config_path,
            self.use_cuda,
        )

    def load_models(self):
        if self.model_name is not None and not self.model_path:
            (
                self.model_path,
                self.config_path,
                self.model_item,
            ) = self.manager.download_model(self.model_name)
        self.vocoder_name = (
            self.model_item["default_vocoder"]
            if self.vocoder_name is None
            else self.vocoder_name
        )

        if self.vocoder_name is not None and not self.vocoder_path:
            (
                self.vocoder_path,
                self.vocoder_config_path,
                _,
            ) = self.manager.download_model(self.vocoder_name)

    def load_customized_models(
        self,
        model_path=None,
        config_path=None,
        speakers_file_path=None,
        vocoder_path=None,
        vocoder_config_path=None,
        encoder_path=None,
        encoder_config_path=None,
    ):
        """
        set custome model paths
        """
        if self.model_path is not None:
            self.model_path = model_path
            self.config_path = config_path
            self.speakers_file_path = speakers_file_path

        if self.vocoder_path is not None:
            self.vocoder_path = vocoder_path
            self.vocoder_config_path = vocoder_config_path

        if self.encoder_path is not None:
            self.encoder_path = encoder_path
            self.encoder_config_path = encoder_config_path

    def list_pretrained_models(self):
        self.manager.list_models()
        sys.exit()

    def synthesize(
        self,
        text,
        save_wav=True,
        out_path="audio_outputs/tts_output.wav",
    ):

        # add utterance delimiters
        UTTERANCE_DELIMITERS = {
            "es-ES": ". ",
            "en-US": ". ",
            "zh": "。",
        }
        text = (
            text + UTTERANCE_DELIMITERS[self.language]
            if text[-1] not in ["。", "，", ".", ",", "!", "?"]
            else text
        )
        print(" > Text: {}".format(text))

        # generate tts
        wav = self.synthesizer.tts(text, self.speaker_idx, self.speaker_wav)

        # save output
        if save_wav:
            print(" > Saving output to {}".format(out_path))
            self.synthesizer.save_wav(wav, out_path)

        return wav
