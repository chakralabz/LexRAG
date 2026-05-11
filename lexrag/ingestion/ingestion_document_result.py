"""Per-document ingestion outcome record."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IngestionDocumentResult:
    """Capture the outcome of ingesting one source document."""

    path: str
    status: str
    chunks_created: int
    fallback_reason: str | None = None
    parse_failure_reason: str | None = None
