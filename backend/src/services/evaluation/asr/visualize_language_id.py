import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageColor

from language_id import parse_language_id_block
from utils import get_duration_seconds

LANGUAGE_COLORS = {
    "en-US": ImageColor.getrgb("blue"),
    "zh": ImageColor.getrgb("red"),
    "es-ES": ImageColor.getrgb("yellow"),
    "pt-BR": ImageColor.getrgb("green"),
    "silence": ImageColor.getrgb("gray"),
}


def load_language_ids(language_id_path: Path):
    language_ids = {}
    # Parse language ID files
    with open(language_id_path) as language_id_file:
        block = []
        for line in language_id_file:
            line = line.strip()
            if line == "":
                # Parse block
                file_id, intervals = parse_language_id_block(block)
                language_ids[file_id] = intervals
                block = []
            else:
                block.append(line)
        if len(block):
            file_id, intervals = parse_language_id_block(block)
        language_ids[file_id] = intervals

    return language_ids


def generate_images(language_ids, wav_file_dir, output_dir):
    IMAGE_WIDTH, IMAGE_HEIGHT = 800, 100

    for file_id, intervals in language_ids.items():
        img = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT))

        duration = get_duration_seconds(str(wav_file_dir / f"{file_id}.wav"))
        for i in range(len(intervals)):
            start_time, language = intervals[i]
            if i + 1 >= len(intervals):
                end_time = duration
            else:
                end_time = intervals[i + 1][0]

            # TODO - draw language ID rectangles
            language_rect = ImageDraw.Draw(img)
            language_rect.rectangle(
                [
                    (IMAGE_WIDTH * (start_time / duration), 0),
                    (IMAGE_WIDTH * (end_time / duration), IMAGE_HEIGHT),
                ],
                fill=LANGUAGE_COLORS[language],
            )
        img.save(output_dir / f"{file_id}.png")


def main(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    language_ids = load_language_ids(args.language_id_path)
    generate_images(language_ids, args.wav_file_dir, args.output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--language_id_path", type=Path)
    parser.add_argument("-w", "--wav_file_dir", type=Path)
    parser.add_argument("-o", "--output_dir", type=Path)
    args = parser.parse_args()
    main(args)
