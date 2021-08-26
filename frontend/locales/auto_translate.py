# Machine translate localization strings.
# This code translates values in a JSON object and writes them back
# To do this nicely, it outputs all of the files it touches in a standardized way

# Note: This code relies on dicts maintaining insertion order (python 3.7+)
# In the future, we can do nice things like only merge in missing translations
# but this will require some discussion with translators and looking at existing tools.

from argparse import ArgumentParser
from functools import partial
import json
import os
from pathlib import Path
import re
from sys import version_info
import warnings

import dotenv
import requests

if version_info < (3, 7):
    raise Exception(
        "This script relies on ordered dictionaries to output locale files in order"
    )

if not os.path.isfile("../.env"):
    raise FileNotFoundError("could not find .env, run from backend directory")
dotenv.load_dotenv("../../.env")

parser = ArgumentParser("Automatically translate our a json languages file")
parser.add_argument(
    "-s", "--source_language", default="en-US", help="base language to translate from"
)
parser.add_argument(
    "-t",
    "--target_languages",
    default=["zh", "es-ES", "pt-BR"],
    nargs="+",
    help="target language(s) to translate to",
)

url = os.getenv("DIDI_TRANSLATE_URL")
apikey = os.getenv("DIDI_TRANSLATE_KEY")


def translate_text(text, source_language, target_language):
    """Mostly copied from didi_translator.py"""
    data = {
        "text": text,
        "source": source_language[:2],  # didi translate uses 2-letter codes
        "target": target_language[:2],
    }

    translation_text = ""
    # encode dict to json format
    encoded_data = json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json", "apikey": apikey}
    req = requests.post(url, headers=headers, data=encoded_data)

    req_dict = req.json()
    try:
        ret_code = req_dict["code"]

        if ret_code == 0:
            translation_text = req_dict["data"]["translation"]
        else:
            warnings.warn(f"Return code from DiDi MT API is not 0 ({ret_code})")
            print(req_dict)
    except ValueError:
        raise Exception("Could not parse JSON response from DiDi translator")

    return translation_text


def post_process(new_s, original_s):
    """Fix html and braces"""

    # Fix html brackets
    new_s = re.sub(r"<\s+(/?[\w]+)\s+>", r"\1", new_s)

    # Restore original text in braces
    def get_original_braces():
        original = re.findall(r"\{.+?\}", original_s)
        for m in original:
            # yield '{' + m + '}'
            yield m
        while True:
            yield ""

    iterable = get_original_braces()
    new_s = re.sub(r"\{.+?\}", lambda x: next(iterable), new_s)

    return new_s


def translate_object(obj, translate):
    """Translates values in obj"""
    if isinstance(obj, str):
        if obj.startswith("@:"):
            return obj  # don't translate linked locale messages
        else:
            return post_process(translate(obj), obj)
    elif isinstance(obj, list):
        return [translate_object(o, translate) for o in obj]
    elif isinstance(obj, dict):
        return {k: translate_object(v, translate) for k, v in obj.items()}
    else:
        warnings.warn("Found a non-string, terminal value:", obj)
        return obj


if __name__ == "__main__":
    args = parser.parse_args()
    assert (
        args.source_language not in args.target_languages
    ), "Cannot translate language to itself"

    source_file = Path(__file__).parent / (args.source_language + ".json")
    with open(source_file, "r") as source_fh:
        source_obj = json.load(source_fh)

    # dump a formatted version of source_file back to maintain consistent formatting
    with open(source_file, "w") as source_fh:
        json.dump(source_obj, source_fh, ensure_ascii=False, indent=4)

    # create versions of the file in each target language
    for target_lang in args.target_languages:
        target_file = Path(__file__).parent / (target_lang + ".json")

        if target_file.is_file():
            warnings.warn(
                f"Skipping language {target_lang} because a file already exists."
                "Move or delete the old file to continue"
            )
            continue

        translate = partial(
            translate_text,
            source_language=args.source_language,
            target_language=target_lang,
        )
        target_obj = translate_object(source_obj, translate)
        with open(target_file, "w") as target_fh:
            json.dump(target_obj, target_fh, ensure_ascii=False, indent=4)

        print(f"Done creating file for {target_lang}")
