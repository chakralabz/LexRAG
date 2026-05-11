"""Parser backend implementations."""

from __future__ import annotations

from .base_document_parser import BaseDocumentParser
from .docling_backend import DoclingParser
from .html_text_extractor import HtmlTextExtractor
from .manual_recovery_parser import ManualRecoveryParser
from .ocr_only_backend import OCROnlyParser
from .pymupdf_parser import PyMuPDFParser
from .unstructured_parser import UnstructuredParser

__all__ = [
    "BaseDocumentParser",
    "DoclingParser",
    "HtmlTextExtractor",
    "ManualRecoveryParser",
    "OCROnlyParser",
    "PyMuPDFParser",
    "UnstructuredParser",
]
