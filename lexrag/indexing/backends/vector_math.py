"""Numerical helpers shared by dense storage backends."""

from __future__ import annotations

import math


def cosine_similarity(lhs: list[float], rhs: list[float]) -> float:
    """Compute cosine similarity for two vectors.

    Args:
        lhs: First vector.
        rhs: Second vector.

    Returns:
        Cosine similarity, or `0.0` when either vector is empty or degenerate.
    """

    if not lhs or not rhs:
        return 0.0
    dot_product = sum(left * right for left, right in zip(lhs, rhs, strict=False))
    lhs_norm = math.sqrt(sum(value * value for value in lhs))
    rhs_norm = math.sqrt(sum(value * value for value in rhs))
    if lhs_norm == 0.0 or rhs_norm == 0.0:
        return 0.0
    return dot_product / (lhs_norm * rhs_norm)
