"""Similarity helpers used by the vector lifecycle package."""

from __future__ import annotations

import math


class VectorSimilarityEngine:
    """Computes cosine similarity for embedded chunks.

    The embedding pipeline normalizes vectors before they reach this layer, but
    this helper still guards against empty or degenerate vectors. That keeps the
    deduplication contract robust when tests or partial ingests bypass normal
    embedding generation.
    """

    def cosine_similarity(self, lhs: list[float], rhs: list[float]) -> float:
        """Return cosine similarity for two vectors.

        Args:
            lhs: First embedding vector.
            rhs: Second embedding vector.

        Returns:
            Cosine similarity in the range `[-1.0, 1.0]`, or `0.0` for invalid
            inputs.
        """

        if not lhs or not rhs:
            return 0.0
        denominator = self._vector_norm(vector=lhs) * self._vector_norm(vector=rhs)
        if denominator == 0.0:
            return 0.0
        return self._dot_product(lhs=lhs, rhs=rhs) / denominator

    def _dot_product(self, *, lhs: list[float], rhs: list[float]) -> float:
        return sum(left * right for left, right in zip(lhs, rhs, strict=False))

    def _vector_norm(self, *, vector: list[float]) -> float:
        return math.sqrt(sum(value * value for value in vector))
