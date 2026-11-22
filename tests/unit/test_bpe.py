
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "practice")
)

from bpe_from_scratch import (
    initialize_vocabulary,
    get_pair_frequencies,
    merge_pair,
    tokenize_word,
)


def test_pair_frequency():
    corpus = {"newest": 6, "widest": 3}
    vocabulary = initialize_vocabulary(corpus)

    frequencies = get_pair_frequencies(vocabulary)

    assert frequencies[("e", "s")] == 9


def test_merge_pair():
    vocabulary = {
        ("e", "s", "t", "</w>"): 2
    }

    result = merge_pair(("e", "s"), vocabulary)

    assert result == {
        ("es", "t", "</w>"): 2
    }


def test_tokenize_word():
    merge_rules = [
        ("e", "s"),
        ("es", "t"),
        ("est", "</w>"),
        ("l", "o"),
        ("lo", "w"),
    ]

    result = tokenize_word("lowest", merge_rules)

    assert result == ["low", "est</w>"]


def test_unknown_characters():
    merge_rules = [
        ("e", "s"),
        ("es", "t"),
    ]

    result = tokenize_word("xyz", merge_rules)

    assert result == ["x", "y", "z", "</w>"]

def test_empty_word():
    merge_rules = [
        ("e", "s"),
        ("es", "t"),
    ]

    result = tokenize_word("", merge_rules)

    assert result == ["</w>"]
