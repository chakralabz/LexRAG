"""Document metadata contract for citation enrichment."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class CitationDocument(BaseModel):
    """Canonical document metadata used during citation resolution.

    Attributes:
        document_id: Stable document identifier used by chunks and indexes.
        title: Human-readable title shown in prompts and audit logs.
        version: Optional version label for source continuity.
        document_date: Optional business-effective date used for display.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    version: str | None = Field(default=None)
    document_date: date | None = Field(default=None)
