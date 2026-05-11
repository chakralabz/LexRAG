"""TableFormer modes supported by Docling."""

from __future__ import annotations

from enum import StrEnum


class DoclingTableMode(StrEnum):
    """Enumerate stable TableFormer mode values."""

    FAST = "fast"
    ACCURATE = "accurate"
