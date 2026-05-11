"""Validation result contract for generated answer citations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.citation.schemas.citation_reference import CitationReference
from lexrag.citation.schemas.citation_validation_issue import (
    CitationValidationIssue,
)


class CitationValidationResult(BaseModel):
    """Summarizes whether generated citations match the context window.

    Attributes:
        is_valid: Whether every cited ID exists in the resolved context.
        references: Atomic references parsed from the generated answer.
        cited_citation_ids: Valid citation IDs actually used by the answer.
        orphan_citation_ids: Referenced IDs that do not exist in context.
        uncited_citation_ids: Available sources that the answer never cited.
        issues: Structured issue records for observability and gating.
    """

    model_config = ConfigDict(frozen=True)

    is_valid: bool
    references: list[CitationReference] = Field(default_factory=list)
    cited_citation_ids: list[int] = Field(default_factory=list)
    orphan_citation_ids: list[int] = Field(default_factory=list)
    uncited_citation_ids: list[int] = Field(default_factory=list)
    issues: list[CitationValidationIssue] = Field(default_factory=list)
