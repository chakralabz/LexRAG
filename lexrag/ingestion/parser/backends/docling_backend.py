"""Docling-backed parser implementation.

This backend deliberately keeps only thin adapter logic. The Docling-specific
configuration, warmup, and result normalization live in dedicated helper
modules so the backend remains easy to reason about.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexrag.ingestion.parser.backends.base_document_parser import BaseDocumentParser
from lexrag.ingestion.parser.builders import ParsedBlockBuilder
from lexrag.ingestion.parser.docling import (
    DoclingConverterFactory,
    DoclingResultNormalizer,
    DoclingRuntime,
)
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock
from lexrag.ingestion.parser.schemas.parser_config import ParserConfig


class DoclingParser(BaseDocumentParser):
    """Parse rich documents with Docling.

    Docling is the high-fidelity path for native PDFs because it can preserve
    structure such as headings, captions, layout regions, and tables better
    than plain text extractors.
    """

    def __init__(
        self,
        *,
        config: ParserConfig | None = None,
        block_builder: ParsedBlockBuilder | None = None,
        converter: Any | None = None,
    ) -> None:
        # The backend shares ParserConfig with the orchestrator so routing and
        # runtime behavior stay aligned during both normal execution and tests.
        self.config = config or ParserConfig()
        self.block_builder = block_builder or ParsedBlockBuilder()
        self.converter: Any | None = converter
        self.converter_factory = DoclingConverterFactory(config=self.config.docling)
        self.runtime = DoclingRuntime(config=self.config.docling)
        self.normalizer = DoclingResultNormalizer(block_builder=self.block_builder)
        self.options_factory = self.converter_factory.options_factory

    def parse(self, path: Path) -> list[ParsedBlock]:
        """Parse a document path into canonical parsed blocks."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        # Conversion and normalization are split so Docling runtime failures are
        # easier to diagnose than post-conversion normalization issues.
        result = self._convert(path)
        return self.normalizer.normalize(
            result=result,
            path=path,
            parser_name=self.parser_name,
        )

    def preload(self) -> None:
        """Warm Docling models and pipeline state before serving requests.

        Warmup has three separate steps:
        1. validate configured artifact paths
        2. optionally prefetch missing models
        3. initialize the PDF pipeline so the first parse call is not cold
        """
        converter = self._get_converter()
        self.runtime._validate_artifacts_path()
        self.runtime._prefetch_artifacts_if_requested()
        self._initialize_pdf_pipeline(converter=converter)

    def _convert(self, path: Path) -> Any:
        """Run Docling conversion and normalize backend exceptions."""
        try:
            converter = self._get_converter()
            return converter.convert(str(path))
        except Exception as exc:
            raise RuntimeError(f"Docling failed to parse {path}") from exc

    def _get_converter(self) -> Any:
        """Build the converter lazily so startup cost is opt-in via preload()."""
        if self.converter is None:
            self.converter = self._build_converter()
        return self.converter

    def _build_converter(self) -> Any:
        """Delegate converter construction to the dedicated factory."""
        return self.converter_factory.build()

    def _build_pdf_pipeline_options(self) -> Any:
        """Expose pipeline option building for focused unit tests."""
        return self.options_factory.build()

    def _apply_common_pipeline_options(self, *, options: Any) -> None:
        self.options_factory._apply_common_pipeline_options(options=options)

    def _apply_table_options(self, *, options: Any) -> None:
        self.options_factory._apply_table_options(options=options)

    def _apply_table_mode(self, *, table_options: Any) -> None:
        self.options_factory._apply_table_mode(table_options=table_options)

    def _apply_accelerator_options(self, *, options: Any) -> None:
        self.options_factory._apply_accelerator_options(options=options)

    def _apply_ocr_options(self, *, options: Any) -> None:
        """Apply OCR options only when an engine-specific options object exists."""
        ocr_options = self._build_ocr_options()
        if ocr_options is not None:
            self.options_factory._set_if_present(options, "ocr_options", ocr_options)

    def _build_ocr_options(self) -> Any | None:
        """Build the Docling OCR options object for the configured engine."""
        config = self.config.docling.ocr
        ocr_class = self._resolve_ocr_options_class(engine=config.engine.value)
        if ocr_class is None:
            return None
        options = ocr_class()
        # Docling exposes different fields depending on the OCR engine, so the
        # shared setter quietly skips unsupported options instead of failing.
        setter = self.options_factory._set_if_present
        setter(options, "lang", list(config.languages) or None)
        setter(options, "force_full_page_ocr", config.force_full_page_ocr)
        setter(options, "bitmap_area_threshold", config.bitmap_area_threshold)
        setter(options, "confidence_threshold", config.confidence_threshold)
        setter(options, "model_storage_directory", config.model_storage_directory)
        setter(options, "download_enabled", config.download_enabled)
        setter(options, "use_gpu", config.use_gpu)
        setter(options, "path", config.tesseract_data_path)
        setter(options, "psm", config.tesseract_page_segmentation_mode)
        return options

    def _resolve_ocr_options_class(self, *, engine: str) -> Any | None:
        """Resolve the engine-specific Docling OCR options class."""
        return self.options_factory._resolve_ocr_options_class(engine=engine)

    def _initialize_pdf_pipeline(self, *, converter: Any) -> None:
        self.runtime._initialize_pdf_pipeline(converter=converter)

    def _build_defaults(self, *, path: Path) -> dict[str, Any]:
        return self.normalizer._build_defaults(path=path, parser_name=self.parser_name)

    def _build_structured_block(
        self,
        *,
        path: Path,
        defaults: dict[str, Any],
        item: Any,
        order: int,
        text: str,
    ):
        """Expose structured-block construction for unit tests and adapters."""
        return self.normalizer._build_structured_block(
            path=path,
            defaults=defaults,
            item=item,
            order=order,
            text=text,
            parser_name=self.parser_name,
        )

    def _resolve_item_text(self, *, item: Any) -> str:
        """Expose item-text resolution for unit tests."""
        return self.normalizer._resolve_item_text(item=item)

    def _normalize_bbox(self, *, value: Any):
        """Expose bbox normalization for unit tests."""
        return self.normalizer._normalize_bbox(value=value)
