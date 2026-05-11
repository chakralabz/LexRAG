"""Create Docling converters with explicit pipeline options."""

from __future__ import annotations

from typing import Any

from lexrag.ingestion.parser.docling.pipeline_options_factory import (
    DoclingPipelineOptionsFactory,
)
from lexrag.ingestion.parser.schemas.docling_config import DoclingConfig


class DoclingConverterFactory:
    """Build Docling converters using parser-owned configuration."""

    def __init__(self, *, config: DoclingConfig) -> None:
        self.config = config
        self.options_factory = DoclingPipelineOptionsFactory(config=config)

    def build(self) -> Any:
        """Build the Docling converter using explicit production defaults."""
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.document_converter import DocumentConverter, PdfFormatOption
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Docling is not installed. Install Docling OCR extras for parsing."
            ) from exc
        pdf_options = self.options_factory.build()
        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
            }
        )
