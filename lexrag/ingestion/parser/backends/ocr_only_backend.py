"""OCR-only parser for scanned PDFs and standalone image documents.

This backend owns the "rasterize first, OCR second" path for documents where
native text extraction is unavailable or unreliable.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from lexrag.ingestion.parser.backends.base_document_parser import BaseDocumentParser
from lexrag.ingestion.parser.builders import ParsedBlockBuilder
from lexrag.ingestion.parser.ocr import (
    OCRExtractor,
    PdfPageRasterizer,
    TesseractOCRExtractor,
)
from lexrag.ingestion.parser.schemas.ocr_text_block import OCRTextBlock
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock
from lexrag.ingestion.parser.schemas.parser_config import ParserConfig
from lexrag.ingestion.parser.schemas.rasterized_page import RasterizedPage


class OCROnlyParser(BaseDocumentParser):
    """Parse scanned PDFs and image documents with OCR."""

    _SUPPORTED_SUFFIXES = frozenset(
        {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    )

    def __init__(
        self,
        *,
        config: ParserConfig | None = None,
        ocr_extractor: OCRExtractor | None = None,
        pdf_rasterizer: PdfPageRasterizer | None = None,
        block_builder: ParsedBlockBuilder | None = None,
    ) -> None:
        # The OCR extractor and rasterizer are injectable so tests can avoid
        # external binaries and expensive PDF rendering work.
        self.config = config or ParserConfig()
        self.ocr_extractor = ocr_extractor or TesseractOCRExtractor(
            config=self.config.ocr
        )
        self.block_builder = block_builder or ParsedBlockBuilder()
        self.pdf_rasterizer = pdf_rasterizer or PdfPageRasterizer(
            dpi=self.config.ocr_render_dpi
        )

    @property
    def parser_name(self) -> str:
        """Return the stable routing name used by orchestration."""
        return "ocr_only"

    def preload(self) -> None:
        """Warm or validate OCR dependencies during application startup."""
        if not self.config.ocr.preload_backend:
            return
        preload = getattr(self.ocr_extractor, "preload", None)
        if callable(preload):
            preload()

    def parse(self, path: Path) -> list[ParsedBlock]:
        """Parse one scanned document path into OCR-backed parsed blocks."""
        self._validate_path(path=path)
        if path.suffix.lower() == ".pdf":
            return self._parse_pdf(path=path)
        return self._parse_image(path=path)

    def _validate_path(self, *, path: Path) -> None:
        """Reject missing files and unsupported file families early."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if path.suffix.lower() in self._SUPPORTED_SUFFIXES:
            return
        raise RuntimeError(f"OCR parser does not support extension: {path.suffix}")

    def _parse_pdf(self, *, path: Path) -> list[ParsedBlock]:
        """Rasterize a PDF into page images, then OCR page by page."""
        with TemporaryDirectory(prefix="lexrag_ocr_") as temp_dir:
            pages = self.pdf_rasterizer.rasterize(
                path=path,
                output_dir=Path(temp_dir),
            )
            return self._blocks_from_pages(path=path, image_pages=pages)

    def _parse_image(self, *, path: Path) -> list[ParsedBlock]:
        """OCR a single image document as page 1."""
        ocr_blocks = self.ocr_extractor.extract(image_path=path, page_number=1)
        return self._parsed_blocks(path=path, ocr_blocks=ocr_blocks)

    def _blocks_from_pages(
        self,
        *,
        path: Path,
        image_pages: list[RasterizedPage],
    ) -> list[ParsedBlock]:
        """OCR each rasterized page and flatten the results into one list."""
        blocks: list[ParsedBlock] = []
        for page in image_pages:
            # Page-by-page OCR keeps memory use bounded and makes per-page
            # failures easier to diagnose than an all-pages-at-once approach.
            ocr_blocks = self.ocr_extractor.extract(
                image_path=page.image_path,
                page_number=page.page_number,
            )
            blocks.extend(self._parsed_blocks(path=path, ocr_blocks=ocr_blocks))
        if blocks:
            return blocks
        raise RuntimeError(f"OCR parser produced no text for {path}")

    def _parsed_blocks(
        self,
        *,
        path: Path,
        ocr_blocks: list[OCRTextBlock],
    ) -> list[ParsedBlock]:
        """Convert OCR text blocks into canonical parsed blocks."""
        if not ocr_blocks:
            raise RuntimeError(f"OCR produced no usable text for {path}")
        return [self._build_block(path=path, block=block) for block in ocr_blocks]

    def _build_block(self, *, path: Path, block: OCRTextBlock) -> ParsedBlock:
        """Build one canonical parsed block from one OCR output region."""
        return self.block_builder.build(
            path=path,
            parser_name=self.parser_name,
            page=block.page,
            section=f"OCR Page {block.page}",
            text=block.text,
            markdown=block.text,
            bbox=block.bbox,
            order_in_page=block.order,
            is_ocr=True,
            confidence=block.confidence,
            ocr_used=self._ocr_backend_name(),
            parse_confidence=block.confidence,
            metadata=self._metadata(),
        )

    def _metadata(self) -> dict[str, object]:
        """Return stable OCR provenance attached to every emitted block."""
        return {
            "parser": self.parser_name,
            "extraction_mode": "ocr",
            "ocr_engine": self.config.ocr.engine.value,
            "ocr_languages": list(self.config.ocr.languages),
        }

    def _ocr_backend_name(self) -> str:
        """Normalize backend class names into compact provenance identifiers."""
        return self.ocr_extractor.__class__.__name__.removesuffix("Extractor").lower()
