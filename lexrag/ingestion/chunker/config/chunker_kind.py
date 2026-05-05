"""Enum of supported top-level chunker implementations."""

from __future__ import annotations

from enum import StrEnum


class ChunkerKind(StrEnum):
    """Stable identifiers for chunker implementations."""

    FIXED = "fixed"
    SEMANTIC = "semantic"
