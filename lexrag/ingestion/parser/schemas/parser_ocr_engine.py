"""OCR engines supported by the standalone OCR parser."""

from __future__ import annotations

from enum import StrEnum


class ParserOcrEngine(StrEnum):
    """Enumerate OCR engines available for OCR-only parsing."""

    TESSERACT_CLI = "tesseract_cli"
