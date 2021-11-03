import argparse
import re
import os
from dotenv import load_dotenv

from nemo.collections.nlp.models import PunctuationCapitalizationModel

from flask import Flask, request
from flask_cors import CORS


class PunctuationCapitalizationServer(object):
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app, cors_allowed_origins="*")
        self.setup_rest_endpoints()

        self.model = {}
        self.load_models()

        # customized words
        self.customized_words = {
            "universal": {"asr": "ASR", "mt": "MT"},
            "en-US": {},
            "es-ES": {},
            "pt-BR": {},
        }

    def load_models(self):
        model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

        # load models
        self.model = {
            "en-US": PunctuationCapitalizationModel.from_pretrained(
                "punctuation_en_bert"
            )
        }

        es_model_path = os.path.join(model_dir, "es.nemo")
        if os.path.exists(es_model_path):
            self.model["es-ES"] = PunctuationCapitalizationModel.restore_from(
                restore_path=es_model_path
            )
        else:
            print(f"Unable to find es-ES model at: {es_model_path}.")

        pt_model_path = os.path.join(model_dir, "pt.nemo")
        if os.path.exists(pt_model_path):
            self.model["pt-BR"] = PunctuationCapitalizationModel.restore_from(
                restore_path=pt_model_path
            )
        else:
            print(f"Unable to find pt-BR model at: {pt_model_path}.")

        zh_model_path = os.path.join(model_dir, "zh.nemo")
        if os.path.exists(zh_model_path):
            self.model["zh"] = PunctuationCapitalizationModel.restore_from(
                restore_path=zh_model_path
            )
        else:
            print(f"Unable to find zh model at: {zh_model_path}.")

    def setup_rest_endpoints(self):
        @self.app.route("/punctuate_and_capitalize", methods=["POST"])
        def punctuate_and_capitalize():
            payload = request.json

            language = payload["language"]

            if not payload["text"]:
                res = payload["text"]
            elif language not in self.model:
                res = payload["text"]
            else:
                if language == "zh":
                    # split zh sentence into characters
                    text = " ".join(list(payload["text"]))
                else:
                    text = payload["text"]

                # preprocess asr result
                text, placeholder_mapping = self.pre_process(text, language)

                # call nemo punctuation and capitalization api
                res = self.model[language].add_punctuation_capitalization([text])[0]

                # post processing
                res = self.post_process(res, placeholder_mapping, language)

            res = {"text": res}

            return res

    def start(self, port, debug):
        self.app.run(host="0.0.0.0", port=port, debug=debug)

    def pre_process(self, asr_res, language="en-US"):
        # lowercase asr result
        asr_res = asr_res.lower()

        # remove punctuations before send it to the punctuation server
        asr_res = re.sub(r"[\?\.,!，。？！¿]", "", asr_res)

        # replace customized word with placeholders
        placeholder_mapping = {}
        customized_words_dict = {
            **self.customized_words["universal"],
            **self.customized_words.get(language, {}),
        }
        tokens = [item for item in asr_res.split() if item]
        new_tokens = []
        for i, t in enumerate(tokens):
            if t in customized_words_dict:
                mapped_word = customized_words_dict[t]
                placeholder = f"placeholder{i}"
                placeholder_mapping[placeholder] = mapped_word
                new_tokens.append(placeholder)
            else:
                new_tokens.append(t)
        asr_res = " ".join(new_tokens)

        return asr_res, placeholder_mapping

    def post_process(self, asr_res_with_punct, placeholder_mapping, language):
        # language specific post processing
        if language == "es-ES":
            # because one string can include multiple sentences,
            # e.g. "test. test? test.". needs to split string into
            # sentences first and then add "¿" to the sentence that
            # is a questions. "test. ¿test? test."

            # split sentences based on "?" and ".".
            sents = [
                s.strip() for s in re.findall(r"([^?.]+[.?]+)", asr_res_with_punct)
            ]

            # add "¿" to sentences that are questions.
            for i in range(len(sents)):
                if sents[i].endswith("?"):
                    sents[i] = "¿" + sents[i]
            res = " ".join(sents)

        elif language == "zh":
            res = asr_res_with_punct.replace(" ", "")
        else:
            res = asr_res_with_punct

        # replace placeholders with the mapped words
        if placeholder_mapping:
            for k, v in placeholder_mapping.items():
                res = re.sub(k, v, res)
                # sometimes punctuation model may capitalize
                # placeholders
                res = re.sub(k.capitalize(), v, res)

        return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="backend server parser settings")
    parser.add_argument("--port", type=int, default=8006)
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    args = parser.parse_args()

    # Load shared config for frontend and backend
    if not os.path.isfile("../.env"):
        raise FileNotFoundError("could not find .env, run from backend directory")
    load_dotenv(dotenv_path="../.env")

    server = PunctuationCapitalizationServer()
    server.start(args.port, args.debug)
