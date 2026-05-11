"""Antivirus provider options for the file ingestion SDK."""

from __future__ import annotations

from enum import StrEnum


class AntivirusProvider(StrEnum):
    """Enumerate antivirus backends supported by ingestion."""

    NONE = "none"
    CLAMAV = "clamav"
