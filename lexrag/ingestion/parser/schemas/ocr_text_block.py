"""Structured OCR text unit emitted by OCR backends."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OCRTextBlock(BaseModel):
    """Represents one OCR text segment before ParsedBlock normalization."""

    model_config = ConfigDict(frozen=True)

    page: int = Field(ge=1)
    order: int = Field(ge=1)
    text: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    bbox: tuple[float, float, float, float] | None = Field(default=None)
