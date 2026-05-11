"""Embedding generator selection modes."""

from __future__ import annotations

from enum import StrEnum


class EmbeddingMode(StrEnum):
    """Named modes used to resolve embedding backends."""

    PRODUCTION = "production"
    DETERMINISTIC_TEST_ONLY = "deterministic-test-only"
