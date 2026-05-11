"""Structured PII finding emitted by answer validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PIIFinding(BaseModel):
    """Represent one PII match surfaced in generated output."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    kind: str = Field(min_length=1)
    match: str = Field(min_length=1)
    start: int = Field(ge=0)
    end: int = Field(ge=1)
