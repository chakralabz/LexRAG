"""OCR settings for the Docling parser backend."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .docling_ocr_engine import DoclingOcrEngine


class DoclingOcrConfig(BaseModel):
    """Configure the OCR behavior used inside Docling."""

    model_config = ConfigDict(frozen=True)

    engine: DoclingOcrEngine = Field(
        default=DoclingOcrEngine.AUTO,
        description="OCR engine used by Docling when OCR is enabled.",
    )
    languages: tuple[str, ...] = Field(
        default=(),
        description="Optional OCR language codes forwarded to the selected engine.",
    )
    force_full_page_ocr: bool = Field(
        default=False,
        description="Whether Docling should OCR the full page instead of only bitmaps.",
    )
    bitmap_area_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum page-area fraction for bitmap-triggered OCR.",
    )
    confidence_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional OCR confidence threshold for engines that support it.",
    )
    model_storage_directory: str | None = Field(
        default=None,
        description="Optional local directory for OCR model artifacts.",
    )
    download_enabled: bool | None = Field(
        default=None,
        description="Whether OCR engines may download missing artifacts on demand.",
    )
    use_gpu: bool | None = Field(
        default=None,
        description="Whether OCR engines that support it should use GPU acceleration.",
    )
    tesseract_data_path: str | None = Field(
        default=None,
        description="Optional Tesseract tessdata path for Tesseract-based engines.",
    )
    tesseract_page_segmentation_mode: int | None = Field(
        default=None,
        ge=0,
        le=13,
        description="Optional Tesseract page segmentation mode.",
    )
