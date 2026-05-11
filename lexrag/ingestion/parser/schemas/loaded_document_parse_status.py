"""Loaded-document parser pipeline status values."""

from __future__ import annotations

from enum import StrEnum


class LoadedDocumentParseStatus(StrEnum):
    """Enumerate terminal parser-pipeline states for one loaded document."""

    PARSED = "parsed"
    REJECTED = "rejected"
    FAILED = "failed"
    QUARANTINED = "quarantined"
