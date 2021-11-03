"""
Language ID evaluation related functions, for loading
test sets and predictions
"""
from datetime import datetime
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageColor

LANGUAGE_COLORS = {
    "en-US": ImageColor.getrgb("blue"),
    "zh": ImageColor.getrgb("red"),
    "es-ES": ImageColor.getrgb("yellow"),
    "pt-BR": ImageColor.getrgb("green"),
    "silence": ImageColor.getrgb("gray"),
}


def generate_images(language_ids, reference_language_ids, durations, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    IMAGE_WIDTH, IMAGE_HEIGHT = 800, 100

    for file_id, intervals in language_ids.items():
        img = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT))

        duration = durations[file_id]

        for i in range(len(intervals)):
            start_time, language = intervals[i]
            if i + 1 >= len(intervals):
                end_time = duration
            else:
                end_time = intervals[i + 1][0]

            # draw language ID rectangles
            language_rect = ImageDraw.Draw(img)
            language_rect.rectangle(
                [
                    (IMAGE_WIDTH * (start_time / duration), IMAGE_HEIGHT / 2),
                    (IMAGE_WIDTH * (end_time / duration), IMAGE_HEIGHT), 
                ],
                fill=LANGUAGE_COLORS[language],
            )

        reference_intervals = reference_language_ids[file_id]
        for i in range(len(reference_intervals)):
            start_time, language = reference_intervals[i]
            if i + 1 >= len(reference_intervals):
                end_time = duration
            else:
                end_time = reference_intervals[i + 1][0]

            # draw language ID rectangles
            language_rect = ImageDraw.Draw(img)
            language_rect.rectangle(
                [
                    (IMAGE_WIDTH * (start_time / duration), 0),
                    (IMAGE_WIDTH * (end_time / duration), IMAGE_HEIGHT / 2), 
                ],
                fill=LANGUAGE_COLORS[language],
            )
            
        img.save(output_dir / f"{file_id}.png")


def parse_language_id_block(block):
    """
    Helper function for parsing language ID files
    """
    file_id, intervals = block[0], block[1:]
    intervals = [i.split(" - ") for i in intervals]
    ref_time = datetime(1900, 1, 1, 0, 0)
    intervals = [
        (
            (datetime.strptime(start_time, "%M:%S.%f") - ref_time).total_seconds(),
            language,
        )
        for start_time, language in intervals
    ]
    return file_id, intervals


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


