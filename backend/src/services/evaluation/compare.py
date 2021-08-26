"""
Visually comparison between different speech translation systems outputs.

command example to run this script:
 python src/services/evaluation/compare.py
 --systems xxx/outputs/system_name/st
 --output_dir XXX/XXX/
 --test_set dwc2-en-zh
 --src en-US
 --tgt zh

The generated compare file format is like:

========================

SAID: 那是两场的录音。两场的录音。

REF:  Those are recordings for the two. Recordings for the two.

system A:  It's okay. Two recordings. < UNK >.

system B:  That's the recording from the two or two factories.

========================

"""

import argparse
from pathlib import Path
from typing import List
from utils import load_text_file

LEADING_PREFIX_STRING_LENGTH = 12


def load_transcripts(output_path: Path, first_n: int = -1):
    with open(output_path) as output_file:
        # Strip off the utterance ID from the saved file
        predictions = []

        for line in output_file:
            predictions.append(" ".join(line.strip().split(" ")[1:]))

            if first_n > 0 and len(predictions) >= first_n:
                break

    return predictions


def write_list_to_file(
    input_list: List,
    output_path: Path,
):
    with open(output_path, "w", encoding="utf-8") as f:
        for line in input_list:
            f.write("========================")
            f.write("\n")
            for item in line:
                f.write(item + "\n")
                f.write("\n")


def main(args):
    systems = {path.parent.name: path for path in args.systems}
    src_reference, tgt_reference = [], []
    systems_result_dict = {}
    systems_mapping_dict = {}
    for system_name, system_path in systems.items():
        # get reference files
        if src_reference == []:
            src_reference_path = system_path / f"{args.test_set}.ref.{args.src}.txt"
            src_reference = load_text_file(src_reference_path.as_posix())
        if tgt_reference == []:
            tgt_reference_path = system_path / f"{args.test_set}.ref.{args.tgt}.txt"
            tgt_reference = load_text_file(tgt_reference_path.as_posix())

        asr_output_path = system_path / f"{args.test_set}.{args.src}.txt"
        mt_output_path = system_path / f"{args.test_set}.{args.tgt}.txt"

        asr_outputs = load_transcripts(asr_output_path.as_posix())
        mt_outputs = load_text_file(mt_output_path.as_posix())
        systems_mapping_dict[system_name] = len(systems_mapping_dict) + 1
        systems_result_dict[f"System {systems_mapping_dict[system_name]}"] = (
            asr_outputs,
            mt_outputs,
        )
    segments = []
    segments.append(
        [
            f"System {v}:  {k.strip()}".ljust(LEADING_PREFIX_STRING_LENGTH)
            for k, v in systems_mapping_dict.items()
        ]
    )

    for idx in range(len(src_reference)):
        if idx >= len(asr_outputs):
            break
        segment_items = []
        asr_ref_seg = src_reference[idx]
        mt_ref_seg = tgt_reference[idx]
        segment_items.append(
            f"{'SAID:'.ljust(LEADING_PREFIX_STRING_LENGTH)}{asr_ref_seg}"
        )
        for key, value in systems_result_dict.items():
            asr_output_seg = value[0][idx]
            asr_output_seg = asr_output_seg.strip()
            segment_items.append(
                f"{str(key+':').ljust(LEADING_PREFIX_STRING_LENGTH)}{asr_output_seg}"
            )

        segment_items.append(
            f"{'REF:'.ljust(LEADING_PREFIX_STRING_LENGTH)}{mt_ref_seg}"
        )
        for key, value in systems_result_dict.items():
            mt_output_seg = value[1][idx]
            mt_output_seg = mt_output_seg.strip()
            segment_items.append(
                f"{str(key+':').ljust(LEADING_PREFIX_STRING_LENGTH)}{mt_output_seg}"
            )
        segments.append(segment_items)

    if not args.output_dir.exists():
        args.output_dir.mkdir(parents=True, exist_ok=True)
    output_filepath = args.output_dir / "compare.txt"
    write_list_to_file(segments, output_filepath)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate comparision file between of different speech translation systems"
    )
    parser.add_argument(
        "-s",
        "--systems",
        type=Path,
        nargs="+",
        default=[],
        help="List of Paths of different speech translation results",
    )
    parser.add_argument(
        "--test_set",
        type=str,
        help="test set name, e.g. dwc2_en-zh",
    )
    parser.add_argument(
        "--output_dir",
        "-o",
        type=Path,
        default="tmp/compare",
        help="Path to save comparision result",
    )
    parser.add_argument(
        "--src",
        type=str,
        default="en-US",
        help="source language code",
    )
    parser.add_argument(
        "--tgt",
        type=str,
        default="zh",
        help="target language code",
    )
    args = parser.parse_args()
    main(args)
