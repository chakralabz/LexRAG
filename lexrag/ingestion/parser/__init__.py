"""Production-grade document parsing package."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .backends import (
    BaseDocumentParser,
    DoclingParser,
    HtmlTextExtractor,
    ManualRecoveryParser,
    OCROnlyParser,
    PyMuPDFParser,
    UnstructuredParser,
)
from .builders import ParsedBlockBuilder, ParsedBlockFactory
from .docling import (
    DoclingConverterFactory,
    DoclingPipelineOptionsFactory,
    DoclingResultNormalizer,
    DoclingRuntime,
)
from .document_parser_protocol import DocumentParserProtocol
from .ocr import (
    OCRExtractor,
    OcrRuntimeValidator,
    PdfPageRasterizer,
    TesseractOCRExtractor,
)
from .orchestration import (
    DocumentParser,
    LoadedDocumentParserPipeline,
    ManualRecoveryRequiredError,
    ParseConfidenceScorer,
    ParserBackendRegistry,
    ParserChainExecutor,
    ParserProvenanceAnnotator,
    ParserSelectionStrategy,
)
from .schemas import (
    DoclingAcceleratorConfig,
    DoclingAcceleratorDevice,
    DoclingConfig,
    DoclingOcrConfig,
    DoclingOcrEngine,
    DoclingTableMode,
    DocumentParseResult,
    LoadedDocumentParseResult,
    LoadedDocumentParseStatus,
    OCRTextBlock,
    ParseAttempt,
    ParsedBlock,
    ParsedPage,
    ParserBackend,
    ParserConfig,
    ParserOcrConfig,
    ParserOcrEngine,
    ParserPdfRoutingConfig,
    ParserSelection,
    RasterizedPage,
)


def parse_document(path: str | Path) -> list[dict[str, Any]]:
    """Parse a document and return the legacy dictionary payload shape."""
    parser = DocumentParser()
    blocks = parser.parse_document(path)
    return [_block_to_legacy_dict(block) for block in blocks]


def _block_to_legacy_dict(block: ParsedBlock) -> dict[str, Any]:
    return {
        "page": block.page,
        "section": block.section,
        "text": block.text,
        "metadata": dict(block.metadata),
    }


__all__ = [
    "BaseDocumentParser",
    "DoclingAcceleratorConfig",
    "DoclingAcceleratorDevice",
    "DoclingConfig",
    "DoclingConverterFactory",
    "DoclingOcrConfig",
    "DoclingOcrEngine",
    "DoclingParser",
    "DoclingPipelineOptionsFactory",
    "DoclingResultNormalizer",
    "DoclingRuntime",
    "DoclingTableMode",
    "DocumentParseResult",
    "DocumentParser",
    "DocumentParserProtocol",
    "HtmlTextExtractor",
    "LoadedDocumentParserPipeline",
    "LoadedDocumentParseResult",
    "LoadedDocumentParseStatus",
    "ManualRecoveryParser",
    "ManualRecoveryRequiredError",
    "OCRExtractor",
    "OCROnlyParser",
    "OCRTextBlock",
    "OcrRuntimeValidator",
    "ParseAttempt",
    "ParseConfidenceScorer",
    "ParsedBlock",
    "ParsedBlockBuilder",
    "ParsedBlockFactory",
    "ParsedPage",
    "ParserBackend",
    "ParserBackendRegistry",
    "ParserChainExecutor",
    "ParserConfig",
    "ParserOcrConfig",
    "ParserOcrEngine",
    "ParserPdfRoutingConfig",
    "ParserProvenanceAnnotator",
    "ParserSelectionStrategy",
    "ParserSelection",
    "PdfPageRasterizer",
    "PyMuPDFParser",
    "RasterizedPage",
    "TesseractOCRExtractor",
    "UnstructuredParser",
    "parse_document",
]
