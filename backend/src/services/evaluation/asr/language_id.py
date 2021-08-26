"""
Language ID evaluation related functions, for loading
test sets and predictions
"""
from datetime import datetime


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
