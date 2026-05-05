"""Config enum for oversized block handling."""

from __future__ import annotations

from enum import StrEnum


class OversizedChunkStrategy(StrEnum):
    """Policies for blocks that exceed the configured token budget."""

    RECURSIVE = "recursive"
    TOKEN_WINDOW = "token_window"
