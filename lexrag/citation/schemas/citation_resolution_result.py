"""Output contract for resolved citation context."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.citation.schemas.resolved_citation import ResolvedCitation


class CitationResolutionResult(BaseModel):
    """Stores resolved citation metadata for one context window.

    Attributes:
        citations: Ordered citations aligned to the context-builder source list.
        unresolved_document_ids: Document IDs referenced by chunks but missing
            from the optional external document catalog.
    """

    model_config = ConfigDict(frozen=True)

    citations: list[ResolvedCitation] = Field(default_factory=list)
    unresolved_document_ids: list[str] = Field(default_factory=list)

    def citation_ids(self) -> set[int]:
        """Return the set of citation IDs available to the generator."""

        return {citation.citation_id for citation in self.citations}

    def by_chunk_id(self) -> dict[str, ResolvedCitation]:
        """Return resolved citations keyed by canonical chunk identifier."""

        return {citation.chunk_id: citation for citation in self.citations}
