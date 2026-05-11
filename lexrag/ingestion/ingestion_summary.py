"""Ingestion run summary model."""

from __future__ import annotations

from dataclasses import dataclass, field

from lexrag.ingestion.ingestion_document_result import IngestionDocumentResult


@dataclass(frozen=True, slots=True)
class IngestionSummary:
    """Operational summary for an ingestion run."""

    documents_seen: int
    chunks_created: int
    chunks_after_dedup: int
    chunks_indexed: int
    fallback_documents: int = 0
    quarantined_documents: int = 0
    fallback_reason_counts: dict[str, int] = field(default_factory=dict)
    parse_failure_counts: dict[str, int] = field(default_factory=dict)
    document_results: list[IngestionDocumentResult] = field(default_factory=list)
