"""Canonical parser schemas and DTOs."""

from __future__ import annotations

from .docling_accelerator_config import DoclingAcceleratorConfig
from .docling_accelerator_device import DoclingAcceleratorDevice
from .docling_config import DoclingConfig
from .docling_ocr_config import DoclingOcrConfig
from .docling_ocr_engine import DoclingOcrEngine
from .docling_table_mode import DoclingTableMode
from .document_parse_result import DocumentParseResult
from .loaded_document_parse_result import LoadedDocumentParseResult
from .loaded_document_parse_status import LoadedDocumentParseStatus
from .ocr_text_block import OCRTextBlock
from .parse_attempt import ParseAttempt
from .parsed_block import ParsedBlock
from .parsed_page import ParsedPage
from .parser_backend import ParserBackend
from .parser_config import ParserConfig
from .parser_ocr_config import ParserOcrConfig
from .parser_ocr_engine import ParserOcrEngine
from .parser_pdf_routing_config import ParserPdfRoutingConfig
from .parser_selection import ParserSelection
from .rasterized_page import RasterizedPage

__all__ = [
    "DoclingAcceleratorConfig",
    "DoclingAcceleratorDevice",
    "DoclingConfig",
    "DoclingOcrConfig",
    "DoclingOcrEngine",
    "DoclingTableMode",
    "DocumentParseResult",
    "LoadedDocumentParseResult",
    "LoadedDocumentParseStatus",
    "OCRTextBlock",
    "ParseAttempt",
    "ParsedBlock",
    "ParsedPage",
    "ParserBackend",
    "ParserConfig",
    "ParserOcrConfig",
    "ParserOcrEngine",
    "ParserPdfRoutingConfig",
    "ParserSelection",
    "RasterizedPage",
]
