"""Structured issue emitted during citation validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CitationValidationIssue(BaseModel):
    """Describes one validation problem in generated citation usage.

    Attributes:
        code: Stable machine-readable issue code.
        message: Human-readable explanation for logs and operators.
        citation_id: Optional offending citation ID.
        raw_text: Optional raw citation token that triggered the issue.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    citation_id: int | None = Field(default=None, ge=1)
    raw_text: str | None = Field(default=None)
