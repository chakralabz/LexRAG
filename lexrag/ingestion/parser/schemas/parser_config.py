"""SDK-facing configuration for the parser package."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .docling_config import DoclingConfig
from .parser_ocr_config import ParserOcrConfig
from .parser_pdf_routing_config import ParserPdfRoutingConfig


class ParserConfig(BaseModel):
    """Provide one compact config object for parser orchestration.

    Parser configuration intentionally owns only parser behavior such as PDF
    routing heuristics and OCR settings. File validation, path policy, size
    limits, and antivirus belong to ``file_ingestion`` and should be configured
    on the ``FileLoadService`` boundary instead of being duplicated here.
    """

    model_config = ConfigDict(frozen=True)

    pdf_routing: ParserPdfRoutingConfig = Field(
        default_factory=ParserPdfRoutingConfig,
        description="Heuristics used to classify PDF routing strategy.",
    )
    docling: DoclingConfig = Field(
        default_factory=DoclingConfig,
        description="Docling backend settings for PDF parsing.",
    )
    ocr: ParserOcrConfig = Field(
        default_factory=ParserOcrConfig,
        description="OCR backend settings for scanned documents.",
    )

    @classmethod
    def from_options(
        cls,
        *,
        scanned_pdf_min_chars_per_page: int | None = None,
        image_heavy_page_ratio: float | None = None,
        image_heavy_max_chars_per_page: int | None = None,
        ocr_render_dpi: int | None = None,
        ocr_languages: tuple[str, ...] | None = None,
        docling_artifacts_path: str | None = None,
        docling_timeout_seconds: float | None = None,
    ) -> ParserConfig:
        """Build a typed parser config from the most common caller options."""
        defaults = cls()
        return cls(
            pdf_routing=ParserPdfRoutingConfig(
                scanned_pdf_min_chars_per_page=(
                    scanned_pdf_min_chars_per_page
                    if scanned_pdf_min_chars_per_page is not None
                    else defaults.pdf_routing.scanned_pdf_min_chars_per_page
                ),
                image_heavy_page_ratio=(
                    image_heavy_page_ratio
                    if image_heavy_page_ratio is not None
                    else defaults.pdf_routing.image_heavy_page_ratio
                ),
                image_heavy_max_chars_per_page=(
                    image_heavy_max_chars_per_page
                    if image_heavy_max_chars_per_page is not None
                    else defaults.pdf_routing.image_heavy_max_chars_per_page
                ),
            ),
            docling=DoclingConfig(
                artifacts_path=docling_artifacts_path,
                document_timeout_seconds=docling_timeout_seconds,
                accelerator=defaults.docling.accelerator,
                ocr=defaults.docling.ocr,
            ),
            ocr=ParserOcrConfig(
                render_dpi=(
                    ocr_render_dpi
                    if ocr_render_dpi is not None
                    else defaults.ocr.render_dpi
                ),
                languages=ocr_languages or defaults.ocr.languages,
            ),
        )

    @property
    def scanned_pdf_min_chars_per_page(self) -> int:
        """Return the scanned-PDF text-density threshold."""
        return self.pdf_routing.scanned_pdf_min_chars_per_page

    @property
    def image_heavy_page_ratio(self) -> float:
        """Return the image-heavy page-ratio threshold."""
        return self.pdf_routing.image_heavy_page_ratio

    @property
    def image_heavy_max_chars_per_page(self) -> int:
        """Return the maximum text density for image-heavy PDFs."""
        return self.pdf_routing.image_heavy_max_chars_per_page

    @property
    def docling_artifacts_path(self) -> str | None:
        """Return the configured Docling artifact cache path."""
        return self.docling.artifacts_path

    @property
    def docling_timeout_seconds(self) -> float | None:
        """Return the configured Docling per-document timeout."""
        return self.docling.document_timeout_seconds

    @property
    def ocr_render_dpi(self) -> int:
        """Return the OCR rasterization DPI."""
        return self.ocr.render_dpi
