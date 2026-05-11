"""Vector normalization helpers for embedding generation."""

from __future__ import annotations

import math


def normalize(vector: list[float]) -> list[float]:
    """Normalize a vector to unit length."""
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]
