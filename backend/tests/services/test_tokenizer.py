import pytest

from services.tokenizer import get_tokenizer

tokenizer_test_data = [
    (
        "it's a great day! isn't it?",
        "en-US",
        ["it", "'s", "a", "great", "day", "!", "isn", "'t", "it", "?"],
    ),
    ("我爱洛杉矶!", "zh", ["我", "爱", "洛杉矶", "!"]),
    (
        "Gloria, corona de la Patria.",
        "es-ES",
        ["Gloria", ",", "corona", "de", "la", "Patria", "."],
    ),
    (
        "Vida, futuro de la Patria...!",
        "es-ES",
        ["Vida", ",", "futuro", "de", "la", "Patria", "...", "!"],
    ),
]


@pytest.mark.parametrize("s,language,expected", tokenizer_test_data)
def test_tokenize(s, language, expected):
    tokenizer = get_tokenizer(language)
    output = tokenizer.tokenize(s)
    assert output == expected


@pytest.mark.parametrize("s,language,expected", tokenizer_test_data)
def test_detokenize(s, language, expected):
    tokenizer = get_tokenizer(language)
    assert tokenizer.detokenize(expected) == s
