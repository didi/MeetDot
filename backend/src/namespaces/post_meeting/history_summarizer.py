#!/usr/bin/python

# python sys lib
import subprocess as sp
from pathlib import Path
import tempfile
import re

# 3rd party modules, pip installed
import yake
import jieba


def hmm_segmenter(transcript, num_segments, logger):
    HMM_SEGMENTER = Path(__file__).parent / "hmm_segmenter.sh"

    with tempfile.TemporaryDirectory() as tmpdir:
        speaker_info_file = Path(tmpdir) / "speaker_info.data"
        with open(speaker_info_file, "w") as f:
            f.write("\n")
            f.write(" ".join([speaker for speaker, _, _ in transcript]))

        cmd = f"bash {HMM_SEGMENTER} {tmpdir} {num_segments}"
        HMM_SPLIT = "hmm_split"
        SPLIT_FILE = Path(tmpdir) / HMM_SPLIT

        with open(logger.log_dir / "summarizer.log", "a") as f:
            f.write("---------------\n")
            f.write(f">>> {cmd}\n")
            sp.call(cmd, shell=True, stdout=f, stderr=f)
            f.write("---------------\n")

        with open(SPLIT_FILE) as f:
            lines = [l.rstrip("\n") for l in f]
            hmm_split = lines[0]
    return hmm_split


def clip_context(context_string, direction):
    context_splits = re.split("[.?。？]", context_string)
    if (
        len(context_splits) == 1 or context_string == "."
    ):  # no period char in string or just that one character
        return context_string
    else:
        if direction == "left":
            return context_splits[-1]
        else:
            return context_splits[0] + "."  # todo: to add the appropriate punctuation


def extract_context(text, key, n, language):
    """Searches for text, and retrieves n words either side of the
    'search' term, which are returned separately"""

    # HACK: Issue: when using jieba for Chinese - it add more spaces around already tokenized
    #       English words in Chinese text . 'Google ASR' --> 'Google   ASR'
    if (
        language == "zh" and " " in key
    ):  # this is a problem if the search key contains space
        key = r"\s*".join(key.split(" "))

    word = r"[\t ]*([^\t ]+)?"  # exclude linebreak
    text_split = text.split(
        "\n"
    )  # match on split lines to avoid matches spanning multiple lines
    for sent in text_split:
        # add word boundary around keyword
        match = re.search(r"{}[\t ]*\b{}\b{}".format(word * n, key, word * n), sent)
        if match:
            groups = match.groups()
            left_context = " ".join([s for s in groups[:n] if s])
            right_context = " ".join([s for s in groups[n:] if s])
            left_context = clip_context(left_context, "left")
            right_context = clip_context(right_context, "right")
            left_context = "... " + left_context
            right_context = right_context + " ..."

            return left_context, right_context

    left_context = "... "
    right_context = " ..."

    return left_context, right_context


def keyword_extractor(
    history: list, splits: list, summary_config: dict, logger, gold_keywords=None
) -> list:
    language = summary_config["language"]
    # 'zh' does not have region code
    if language == "en-US":
        language = "en"
    elif language == "es-ES":
        language = "es"
    elif language == "pt-BR":
        language = "pt"

    max_ngram_size = summary_config["max_ngram_size"]
    deduplication_threshold = summary_config["deduplication_threshold"]
    num_of_keywords = summary_config["num_of_keywords"]

    custom_kw_extractor = yake.KeywordExtractor(
        lan=language,
        n=max_ngram_size,
        dedupLim=deduplication_threshold,
        top=num_of_keywords,
        features=None,
    )

    segments = read_segments(history, splits)
    keywords_summary = list()

    if gold_keywords:
        with open(gold_keywords) as f:
            all_keywords = [
                [(word, 0) for word in line.rstrip("\n").split(", ")] for line in f
            ]

    for id, (seg_id, segment) in enumerate(segments):
        text = "\n".join([utter for _, utter in segment])
        if language == "zh":
            text = "\n".join([" ".join(jieba.lcut(utter)) for _, utter in segment])
        text = filter_words(text)
        keywords = custom_kw_extractor.extract_keywords(text)
        if gold_keywords:
            keywords = all_keywords[id]

        keywords_with_context = list()
        # HACK: Issue: when using jieba for Chinese - it add more spaces around already tokenized
        #       English words in Chinese text . 'Google ASR' --> 'Google   ASR'
        if language == "zh":
            sorted_keywords = sorted(
                [
                    (
                        re.search(
                            r"\b{}\b".format(r"\s*".join(kw.split(" "))), text
                        ).span(),
                        (kw, score),
                    )
                    for kw, score in keywords
                    if re.search(r"\b{}\b".format(r"\s*".join(kw.split(" "))), text)
                ],
                key=lambda x: x[0],
            )
        else:
            sorted_keywords = sorted(
                [
                    (re.search(r"\b{}\b".format(kw), text).span(), (kw, score))
                    for kw, score in keywords
                    if re.search(r"\b{}\b".format(kw), text)
                ],
                key=lambda x: x[0],
            )
        for _, (word, score) in sorted_keywords:
            left_context, right_context = extract_context(text, word, 3, language)
            left_context, word, right_context = appropriate_spacing(
                word, left_context, right_context, language
            )
            keywords_with_context.append((word, score, left_context, right_context))
        speakers, segment_length = main_speakers(segment, logger)
        keywords_summary.append(
            (seg_id, speakers, keywords_with_context, segment_length)
        )

    return keywords_summary


def filter_words(text):
    words_to_filter = [
        "yeah.",
        "yeah,",
        "Yeah.",
        "Yeah,",
        "yeah",
        "Yeah",
    ]  # todo: other language filler words ?
    for word in words_to_filter:
        text = text.replace(word, "")
    return text


def main_speakers(segment, logger):
    speaker_histogram = {
        speaker: 0 for speaker in set(speaker for speaker, _ in segment)
    }

    segment_length = 0
    for speaker, utter in segment:
        speaker_histogram[speaker] += len(utter.split(" "))
        segment_length += len(utter.split(" "))
    total_words = sum(list(speaker_histogram.values()))
    speaker_histogram_sorted = sorted(
        list(speaker_histogram.items()), key=lambda x: x[1], reverse=True
    )
    main_speakers_list = list()
    cumulative_words = 0
    for speaker, freq in speaker_histogram_sorted:
        main_speakers_list.append(speaker)
        cumulative_words += freq
        if float(cumulative_words) / total_words >= 0.9:
            break

    logger.info("[SUMMARIZER - BEGIN]")
    logger.info(speaker_histogram)
    logger.info("[SUMMARIZER - END]")

    return main_speakers_list, segment_length


def read_segments(history: list, splits: list):
    segments = list()
    prev_seg_id = ""
    segment = list()
    for (speaker, language, utter), seg_id in zip(history, splits):
        if prev_seg_id != "" and prev_seg_id != seg_id:
            segments.append((prev_seg_id, segment))
            segment = list()
        prev_seg_id = seg_id
        segment.append((speaker, utter))
    segments.append((prev_seg_id, segment))
    return segments


def remove_spaces_between_zh_chars(s):
    return re.sub(fr"(?<=[^A-z])\s*(?=[^A-z])", "", s)


def appropriate_spacing(keyword, left, right, language):
    if language == "zh":
        return [remove_spaces_between_zh_chars(s) for s in (left, keyword, right)]

    nbsp = "\xa0"
    spaced_left = left + nbsp
    if right[0].isalpha():
        spaced_right = nbsp + right
    else:
        spaced_right = right

    return spaced_left, keyword, spaced_right


def create_summary_string(summary, summary_config=None):
    if summary_config is not None:
        summary_string = f"Config: {summary_config}\n"
    else:
        summary_string = ""

    for segment_summary in summary:
        speakers = segment_summary["speakers"]
        length = segment_summary["length"]

        key_snippets = segment_summary["key_snippets"]
        topics = "\n            ".join(
            [
                "".join([left, "*" + kw + "*", right])
                for kw, _, left, right in key_snippets
            ]
        )

        summary_string += (
            f"- Speakers: {speakers}\n  Topics  : {topics}\n  Length  : {length}\n\n"
        )
    return summary_string


def history_summary(
    history: list,
    summary_config: dict,
    logger,
    num_segments: int = 6,
    gold_segments=None,
    gold_keywords=None,
) -> list:
    hmm_split = hmm_segmenter(history, num_segments, logger)
    hmm_split = hmm_split.split(" ")
    if gold_segments:
        with open(gold_segments) as f:
            hmm_split = [line.rstrip("\n") for line in f]

    keywords_summary = keyword_extractor(
        history, hmm_split, summary_config, logger, gold_keywords
    )

    summary = list()
    total_meeting_length = sum([seglen for _, _, _, seglen in keywords_summary])
    total_meeting_length = (
        0.1 if total_meeting_length == 0 else total_meeting_length
    )  # to avoid div_by_zero
    for seg_id, main_speakers, key_snippets, segment_length in keywords_summary:
        main_speakers = ", ".join(main_speakers)
        length = (
            f"{float(segment_length) / total_meeting_length * 100:.0f}%"
            if total_meeting_length != 0
            else str(0)
        )
        # filter 0 length segments and empty keyphrase snippets
        if length == "0%" or len(key_snippets) == 0:
            continue
        key_snippets = [
            snippet
            for snippet in key_snippets
            if len(snippet[0]) > 0 and snippet[0] != ""
        ]

        # key_snippets: [(keyphrase: str, score: float, left_context: str, right_context: str), ...]
        summary.append(
            {"speakers": main_speakers, "key_snippets": key_snippets, "length": length}
        )

    summary_string = create_summary_string(summary, summary_config)
    logger.info("[SUMMARIZER - BEGIN]")
    logger.info(summary_string)
    logger.info("[SUMMARIZER - END]")

    return summary
