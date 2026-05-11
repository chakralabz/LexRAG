"""OCR runtime helpers and adapters for parser backends."""

from __future__ import annotations

from .ocr_extractor import OCRExtractor
from .ocr_runtime import OcrRuntimeValidator
from .pdf_page_rasterizer import PdfPageRasterizer
from .tesseract_ocr_extractor import TesseractOCRExtractor

__all__ = [
    "OCRExtractor",
    "OcrRuntimeValidator",
    "PdfPageRasterizer",
    "TesseractOCRExtractor",
]
