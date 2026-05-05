"""Similarity utilities used inside the chunking layer."""

from __future__ import annotations

from collections import Counter


class SimilarityEngine:
    """Compute lexical coherence without depending on embeddings."""

    def score_text_pair(self, left_text: str, right_text: str) -> float:
        """Return a weighted token-overlap score for adjacent text spans."""
        left_counts = self._token_counts(text=left_text)
        right_counts = self._token_counts(text=right_text)
        if not left_counts or not right_counts:
            return 0.0
        shared = sum((left_counts & right_counts).values())
        total = sum((left_counts | right_counts).values())
        if total == 0:
            return 0.0
        return shared / total

    def _token_counts(self, *, text: str) -> Counter[str]:
        """Build normalized token counts for lexical similarity scoring."""
        tokens = [token.lower() for token in text.split() if token.strip()]
        return Counter(tokens)
