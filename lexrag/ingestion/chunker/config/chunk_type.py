"""Enum of canonical retrieval chunk types."""

from __future__ import annotations

from enum import StrEnum


class ChunkType(StrEnum):
    """Normalized chunk categories used across indexing and retrieval."""

    CODE = "code"
    DEFINITION = "definition"
    IMAGE = "image"
    LIST = "list"
    PARAGRAPH = "paragraph"
    TABLE = "table"
