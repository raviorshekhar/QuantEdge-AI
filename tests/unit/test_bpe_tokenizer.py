
import sys
from pathlib import Path
import pytest

CORPUS = {
    "low": 5,
    "lower": 2,
    "newest": 6,
    "widest": 3,
}

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "practice")
)

import pytest

from bpe_tokenizer import BPETokenizer


@pytest.fixture
def trained_tokenizer():
    corpus = {
        "low": 5,
        "lower": 2,
        "newest": 6,
        "widest": 3,
    }

    tokenizer = BPETokenizer()
    tokenizer.train(corpus, num_merges=5)

    return tokenizer


def test_training_learns_merge_rules(trained_tokenizer):
    assert trained_tokenizer.merge_rules == [
        ("e", "s"),
        ("es", "t"),
        ("est", "</w>"),
        ("l", "o"),
        ("lo", "w"),
    ]


def test_encode_word(trained_tokenizer):
    tokens = trained_tokenizer.encode("lowest")

    assert tokens == ["low", "est</w>"]


def test_decode_tokens(trained_tokenizer):
    tokens = trained_tokenizer.encode("lowest")

    decoded = trained_tokenizer.decode(tokens)

    assert decoded == "lowest"


def test_encode_before_training_raises_error():
    tokenizer = BPETokenizer()

    with pytest.raises(RuntimeError):
        tokenizer.encode("lowest")


def test_unknown_characters_are_preserved(trained_tokenizer):
    tokens = trained_tokenizer.encode("xyz")

    assert tokens == ["x", "y", "z", "</w>"]

def test_encode_multiple_words(trained_tokenizer):
    tokens = trained_tokenizer.encode("lowest widest")

    assert trained_tokenizer.decode(tokens) == "lowest widest"


def test_preserve_multiple_spaces(trained_tokenizer):
    text = "lowest   widest"

    tokens = trained_tokenizer.encode(text)

    assert trained_tokenizer.decode(tokens) == text


def test_preserve_punctuation(trained_tokenizer):
    text = "lowest, widest!"

    tokens = trained_tokenizer.encode(text)

    assert trained_tokenizer.decode(tokens) == text


def test_token_ids_support_multiple_words():
    tokenizer = BPETokenizer()
    tokenizer.train(CORPUS, num_merges=5)

    text = "lowest widest"

    token_ids = tokenizer.encode_to_ids(text)
    decoded = tokenizer.decode_from_ids(token_ids)

    assert decoded == text


def test_vocabulary_contains_base_and_merged_tokens():
    tokenizer = BPETokenizer()
    tokenizer.train(CORPUS, num_merges=5)

    assert "l" in tokenizer.token_to_id
    assert "o" in tokenizer.token_to_id
    assert "low" in tokenizer.token_to_id
    assert "est</w>" in tokenizer.token_to_id
    assert "<unk>" in tokenizer.token_to_id


def test_unknown_token_fallback():
    tokenizer = BPETokenizer()
    tokenizer.train(CORPUS, num_merges=5)

    token_ids = tokenizer.encode_to_ids("lowest?")
    decoded = tokenizer.decode_from_ids(token_ids)

    assert decoded == "lowest<unk>"



def test_save_and_load_tokenizer(tmp_path):
    tokenizer = BPETokenizer()
    tokenizer.train(CORPUS, num_merges=5)

    file_path = tmp_path / "tokenizer.json"

    tokenizer.save(file_path)

    loaded_tokenizer = BPETokenizer.load(file_path)

    assert loaded_tokenizer.trained is True
    assert loaded_tokenizer.merge_rules == tokenizer.merge_rules
    assert loaded_tokenizer.token_to_id == tokenizer.token_to_id


def test_loaded_tokenizer_encoding_consistency(tmp_path):
    tokenizer = BPETokenizer()
    tokenizer.train(CORPUS, num_merges=5)

    text = "lowest widest"

    original_ids = tokenizer.encode_to_ids(text)

    file_path = tmp_path / "tokenizer.json"
    tokenizer.save(file_path)

    loaded_tokenizer = BPETokenizer.load(file_path)

    loaded_ids = loaded_tokenizer.encode_to_ids(text)

    assert loaded_ids == original_ids
    assert loaded_tokenizer.decode_from_ids(loaded_ids) == text


def test_save_before_training_raises_error(tmp_path):
    tokenizer = BPETokenizer()

    file_path = tmp_path / "tokenizer.json"

    with pytest.raises(RuntimeError):
        tokenizer.save(file_path)
