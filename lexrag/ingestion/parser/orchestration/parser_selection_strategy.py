"""Deterministic parser selection strategy.

Routing is intentionally conservative: the strategy prefers predictable
selection and explicit fallback order over trying to be too clever in each
document family.
"""

from __future__ import annotations

from pathlib import Path

from lexrag.ingestion.file_ingestion.schemas.file_type_detection import (
    FileTypeDetection,
)
from lexrag.ingestion.file_ingestion.schemas.file_validation_result import (
    FileValidationResult,
)
from lexrag.ingestion.parser.schemas.parser_backend import ParserBackend
from lexrag.ingestion.parser.schemas.parser_config import ParserConfig
from lexrag.ingestion.parser.schemas.parser_selection import ParserSelection


class ParserSelectionStrategy:
    """Choose the parser chain for a document deterministically."""

    def __init__(self, config: ParserConfig | None = None) -> None:
        """Initialize the strategy with parser heuristics.

        Args:
            config: Optional parser configuration.
        """
        self.config = config or ParserConfig()

    def select(
        self,
        *,
        path: Path,
        validation: FileValidationResult,
        detection: FileTypeDetection,
    ) -> ParserSelection:
        """Select the parser order and routing metadata.

        Args:
            path: Document path being parsed.
            validation: Pre-parse validation result.
            detection: File type detection result.

        Returns:
            The deterministic parser routing plan for this document.
        """
        # Encryption is terminal because none of the automated backends can
        # safely or reliably extract content from an inaccessible PDF.
        if validation.encrypted:
            return self._manual_recovery_selection(reason="encrypted_pdf")
        # Standalone images are always OCR-first because there is no native text
        # extraction path analogous to PDF or HTML parsing.
        if detection.detected_type == "image":
            return self._ocr_first_selection(reason="image_document")
        if detection.detected_type == "pdf":
            return self._select_pdf_path(path=path)
        if detection.detected_type in {"html", "text", "office", "xml", "email"}:
            return self._secondary_only_selection(reason=detection.detected_type)
        return self._secondary_only_selection(reason="unsupported_primary_type")

    def _select_pdf_path(self, *, path: Path) -> ParserSelection:
        """Choose the PDF parser route based on lightweight document signals."""
        scanned_pdf = self._is_scanned_pdf(path=path)
        image_heavy = self._is_image_heavy(path=path)
        if scanned_pdf:
            return self._ocr_first_selection(reason="scanned_pdf", scanned_pdf=True)
        if image_heavy:
            # Image-heavy PDFs still give Docling the first chance because some
            # mixed-content documents preserve enough native structure to avoid
            # a full OCR-only pass.
            return ParserSelection(
                primary_parser_name=ParserBackend.DOCLING.value,
                parser_order=[
                    ParserBackend.DOCLING.value,
                    ParserBackend.OCR_ONLY.value,
                    ParserBackend.PYMUPDF.value,
                    ParserBackend.UNSTRUCTURED.value,
                ],
                fallback_chain=[
                    ParserBackend.OCR_ONLY.value,
                    ParserBackend.PYMUPDF.value,
                    ParserBackend.UNSTRUCTURED.value,
                    ParserBackend.MANUAL_RECOVERY.value,
                ],
                route_reason="image_heavy_pdf",
                requires_ocr=True,
                scanned_pdf=False,
                image_heavy=True,
                encrypted=False,
            )
        return ParserSelection(
            primary_parser_name=ParserBackend.DOCLING.value,
            parser_order=[
                ParserBackend.DOCLING.value,
                ParserBackend.PYMUPDF.value,
                ParserBackend.UNSTRUCTURED.value,
                ParserBackend.OCR_ONLY.value,
            ],
            fallback_chain=[
                ParserBackend.PYMUPDF.value,
                ParserBackend.UNSTRUCTURED.value,
                ParserBackend.OCR_ONLY.value,
                ParserBackend.MANUAL_RECOVERY.value,
            ],
            route_reason="native_pdf",
            requires_ocr=False,
            scanned_pdf=False,
            image_heavy=False,
            encrypted=False,
        )

    def _secondary_only_selection(self, *, reason: str) -> ParserSelection:
        """Route non-primary formats to the lightweight parser chain.

        These formats do not benefit from the Docling PDF pipeline, so we use a
        simpler fallback stack that keeps parsing deterministic and cheaper.
        """
        return ParserSelection(
            primary_parser_name=ParserBackend.PYMUPDF.value,
            parser_order=[
                ParserBackend.PYMUPDF.value,
                ParserBackend.UNSTRUCTURED.value,
            ],
            fallback_chain=[
                ParserBackend.UNSTRUCTURED.value,
                ParserBackend.MANUAL_RECOVERY.value,
            ],
            route_reason=reason,
            requires_ocr=False,
            scanned_pdf=False,
            image_heavy=False,
            encrypted=False,
        )

    def _ocr_first_selection(
        self,
        *,
        reason: str,
        scanned_pdf: bool = False,
    ) -> ParserSelection:
        """Route OCR-dependent documents to the OCR-first chain."""
        # Docling still appears in the fallback chain because it can sometimes
        # recover useful layout even after the explicit OCR path fails.
        return ParserSelection(
            primary_parser_name=ParserBackend.OCR_ONLY.value,
            parser_order=[
                ParserBackend.OCR_ONLY.value,
                ParserBackend.DOCLING.value,
                ParserBackend.PYMUPDF.value,
                ParserBackend.UNSTRUCTURED.value,
            ],
            fallback_chain=[
                ParserBackend.DOCLING.value,
                ParserBackend.PYMUPDF.value,
                ParserBackend.UNSTRUCTURED.value,
                ParserBackend.MANUAL_RECOVERY.value,
            ],
            route_reason=reason,
            requires_ocr=True,
            scanned_pdf=scanned_pdf,
            image_heavy=not scanned_pdf,
            encrypted=False,
        )

    def _manual_recovery_selection(self, *, reason: str) -> ParserSelection:
        """Route unparseable documents directly to manual recovery."""
        return ParserSelection(
            primary_parser_name=ParserBackend.MANUAL_RECOVERY.value,
            parser_order=[ParserBackend.MANUAL_RECOVERY.value],
            fallback_chain=[],
            route_reason=reason,
            requires_ocr=False,
            scanned_pdf=False,
            image_heavy=False,
            encrypted=True,
        )

    def _is_scanned_pdf(self, *, path: Path) -> bool:
        """Detect scanned PDFs by low average text volume per page."""
        page_stats = self._pdf_page_stats(path=path)
        if page_stats is None:
            return False
        page_count, total_chars, _image_pages = page_stats
        if page_count == 0:
            return False
        average_chars = total_chars / page_count
        return average_chars < self.config.scanned_pdf_min_chars_per_page

    def _is_image_heavy(self, *, path: Path) -> bool:
        """Detect image-heavy PDFs using page-level image presence."""
        page_stats = self._pdf_page_stats(path=path)
        if page_stats is None:
            return False
        page_count, total_chars, image_pages = page_stats
        if page_count == 0:
            return False
        # We require both a high image ratio and low text density so the OCR
        # route does not steal native PDFs that merely contain a few charts.
        mostly_images = (image_pages / page_count) >= self.config.image_heavy_page_ratio
        sparse_text = (
            total_chars / page_count
        ) < self.config.image_heavy_max_chars_per_page
        return mostly_images and sparse_text

    def _pdf_page_stats(self, *, path: Path) -> tuple[int, int, int] | None:
        """Collect lightweight page statistics with PyMuPDF when available.

        The strategy degrades gracefully when PyMuPDF is unavailable. In that
        case we simply skip the heuristic and fall back to default routing.
        """
        try:
            import fitz
        except Exception:  # pragma: no cover
            return None
        try:
            return self._read_page_stats(path=path, fitz_module=fitz)
        except Exception:
            return None

    def _read_page_stats(self, *, path: Path, fitz_module) -> tuple[int, int, int]:
        """Read page count, total characters, and image-heavy page count."""
        total_chars = 0
        image_pages = 0
        with fitz_module.open(path) as document:  # pragma: no cover
            for page in document:
                page_text = page.get_text("text")
                total_chars += len(page_text.strip())
                if page.get_images(full=True):
                    image_pages += 1
            return len(document), total_chars, image_pages
