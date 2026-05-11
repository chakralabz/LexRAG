"""Validation contract for generated answers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.citation.schemas import CitationValidationResult
from lexrag.generation.schemas.pii_finding import PIIFinding


class GenerationValidation(BaseModel):
    """Summarize post-generation validation for one answer."""

    model_config = ConfigDict(frozen=True)

    citation_validation: CitationValidationResult
    pii_findings: list[PIIFinding] = Field(default_factory=list)
    is_abstained: bool
    is_valid: bool
