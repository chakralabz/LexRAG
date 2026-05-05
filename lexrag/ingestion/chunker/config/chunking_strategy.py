"""Enum of chunk construction strategies."""

from __future__ import annotations

from enum import StrEnum


class ChunkingStrategy(StrEnum):
    """Planner and builder strategy labels."""

    FIXED_TOKEN_WINDOW = "fixed_token_window"
    HEADING_ANCHORED = "heading_anchored"
    RECURSIVE_WINDOW = "recursive_window"
    SEMANTIC_MERGE = "semantic_merge"
    SLIDING_WINDOW = "sliding_window"
    STANDALONE = "standalone"
    TABLE_AWARE = "table_aware"
    UNSPECIFIED = "unspecified"
