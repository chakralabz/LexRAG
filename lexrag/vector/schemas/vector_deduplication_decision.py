"""Audit schema for one vector-level deduplication outcome."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VectorDeduplicationDecision(BaseModel):
    """Captures how one embedded chunk was handled by deduplication.

    Attributes:
        chunk_id: Candidate chunk identifier.
        decision: Stable outcome label such as `kept`, `suppressed`, or
            `cross_document_match`.
        matched_chunk_id: Indexed chunk that triggered the decision, when any.
        matched_doc_id: Lineage identifier for the matched chunk.
        similarity: Similarity score used for the decision.
        reason: Human-readable explanation for the applied policy.
    """

    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(description="Evaluated chunk identifier.")
    decision: str = Field(description="Stable decision label.")
    matched_chunk_id: str | None = Field(default=None)
    matched_doc_id: str | None = Field(default=None)
    similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    reason: str = Field(description="Reason for the applied decision.")
