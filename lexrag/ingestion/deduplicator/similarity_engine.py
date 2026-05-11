"""Token-set similarity engine for deduplication."""

from __future__ import annotations

from lexrag.utils.text import TextNormalizer


class SimilarityEngine:
    """Token-set similarity service used by deduplicators."""

    def __init__(self) -> None:
        self._text_normalizer = TextNormalizer()

    def tokenize_set(self, text: str) -> set[str]:
        """Tokenizes text into normalized unique terms."""
        return self._text_normalizer.token_set_words(text)

    def jaccard_similarity(self, lhs: set[str], rhs: set[str]) -> float:
        """Computes Jaccard similarity between token sets."""
        if not lhs and not rhs:
            return 1.0
        if not lhs or not rhs:
            return 0.0
        intersection = lhs.intersection(rhs)
        union = lhs.union(rhs)
        return len(intersection) / len(union)
