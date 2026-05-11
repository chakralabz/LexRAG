"""Atomic inline citation reference extracted from answer text."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CitationReference(BaseModel):
    """Represents one parsed inline citation occurrence.

    Attributes:
        citation_id: Numeric identifier emitted by the generation layer.
        raw_text: Exact inline token group that contained the reference.
        start_index: Inclusive start character offset in the answer text.
        end_index: Exclusive end character offset in the answer text.
    """

    model_config = ConfigDict(frozen=True)

    citation_id: int = Field(ge=1)
    raw_text: str = Field(min_length=3)
    start_index: int = Field(ge=0)
    end_index: int = Field(ge=1)
