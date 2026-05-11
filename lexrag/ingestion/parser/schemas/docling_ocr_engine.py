"""OCR engine values supported by Docling."""

from __future__ import annotations

from enum import StrEnum


class DoclingOcrEngine(StrEnum):
    """Enumerate OCR engines exposed by Docling pipeline options."""

    AUTO = "auto"
    EASYOCR = "easyocr"
    TESSERACT = "tesseract"
    TESSERACT_CLI = "tesseract_cli"
    OCRMAC = "ocrmac"
    RAPIDOCR = "rapidocr"
