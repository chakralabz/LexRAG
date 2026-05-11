"""PDF routing heuristics for parser selection."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ParserPdfRoutingConfig(BaseModel):
    """Configure lightweight heuristics used to route PDF parsing."""

    model_config = ConfigDict(frozen=True)

    scanned_pdf_min_chars_per_page: int = Field(
        default=50,
        ge=0,
        description="Average character threshold below which a PDF is treated as scanned.",
    )
    image_heavy_page_ratio: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Fraction of pages with images required to mark a PDF image-heavy.",
    )
    image_heavy_max_chars_per_page: int = Field(
        default=200,
        ge=0,
        description="Maximum average characters per page for image-heavy routing.",
    )
