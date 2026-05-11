"""Resolved citation object emitted to the context builder."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ResolvedCitation(BaseModel):
    """Represents one fully resolved source available to generation.

    Attributes:
        citation_id: Numeric source identifier used inline by the model.
        document_title: Human-readable title for prompts and audits.
        document_id: Stable source document identifier.
        document_version: Optional version for citation continuity.
        page: Start page surfaced to users and evaluators.
        section: Optional section lineage string for source lookup.
        heading_anchor: Optional stable anchor for rich clients.
        chunk_id: Canonical chunk identifier that backs the citation.
        source_block_ids: Original block IDs covered by the chunk.
        confidence: Metadata completeness score in ``[0.0, 1.0]``.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    citation_id: int = Field(ge=1)
    document_title: str = Field(min_length=1)
    document_id: str | None = Field(default=None)
    document_version: str | None = Field(default=None)
    page: int = Field(ge=1)
    section: str | None = Field(default=None)
    heading_anchor: str | None = Field(default=None)
    chunk_id: str = Field(min_length=1)
    source_block_ids: tuple[str, ...] = Field(default_factory=tuple)
    confidence: float = Field(ge=0.0, le=1.0)
