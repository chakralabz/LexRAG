from __future__ import annotations

from lexrag.utils.text import TextNormalizer


def test_text_normalizer_tokenization_consistency() -> None:
    text_normalizer = TextNormalizer()
    text = "Alpha, beta! beta"
    assert text_normalizer.tokenize_words(text) == ["alpha", "beta", "beta"]
    assert text_normalizer.token_set_words(text) == {"alpha", "beta"}


def test_text_normalizer_sanitize_identifier() -> None:
    text_normalizer = TextNormalizer()
    assert text_normalizer.sanitize_identifier("My Doc (v1)") == "my_doc_v1"
