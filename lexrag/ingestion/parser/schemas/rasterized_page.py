"""Rasterized page contract used by OCR-capable parsers."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class RasterizedPage(BaseModel):
    """Represents one PDF page rendered to an image for OCR."""

    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    image_path: Path
