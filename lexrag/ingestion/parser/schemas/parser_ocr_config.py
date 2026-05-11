"""OCR settings used by parser backends."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .parser_ocr_engine import ParserOcrEngine


class ParserOcrConfig(BaseModel):
    """Configure OCR rasterization behavior."""

    model_config = ConfigDict(frozen=True)

    engine: ParserOcrEngine = Field(
        default=ParserOcrEngine.TESSERACT_CLI,
        description="OCR backend used by the standalone OCR parser.",
    )
    render_dpi: int = Field(
        default=300,
        ge=72,
        le=600,
        description="Rasterization DPI used before OCRing scanned PDFs.",
    )
    languages: tuple[str, ...] = Field(
        default=(),
        description="Optional OCR languages forwarded to the OCR backend.",
    )
    tesseract_binary: str = Field(
        default="tesseract",
        description="Tesseract executable used by the OCR-only parser.",
    )
    tesseract_data_path: str | None = Field(
        default=None,
        description="Optional tessdata directory for Tesseract language files.",
    )
    tesseract_page_segmentation_mode: int = Field(
        default=6,
        ge=0,
        le=13,
        description="Tesseract page segmentation mode used by the OCR-only parser.",
    )
    preload_backend: bool = Field(
        default=False,
        description="Validate OCR runtime dependencies during parser warmup.",
    )
