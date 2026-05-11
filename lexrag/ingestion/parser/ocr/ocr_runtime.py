"""Standalone OCR runtime validation helpers.

The OCR-only parser depends on a system-level Tesseract installation, so these
checks are kept separate from parsing logic and can be run during service
startup.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from lexrag.ingestion.parser.schemas.parser_ocr_config import ParserOcrConfig


class OcrRuntimeValidator:
    """Validate OCR runtime dependencies before live traffic starts."""

    def __init__(self, *, config: ParserOcrConfig) -> None:
        self.config = config

    def validate(self) -> None:
        """Fail fast when required OCR runtime components are unavailable."""
        self._require_tesseract_binary()
        self._require_tessdata_path()

    def _require_tesseract_binary(self) -> None:
        """Require that the configured Tesseract executable is on PATH."""
        if shutil.which(self.config.tesseract_binary):
            return
        raise RuntimeError(
            "Tesseract CLI is required for OCR parsing. "
            f"Configured binary not found: {self.config.tesseract_binary}"
        )

    def _require_tessdata_path(self) -> None:
        """Require that the configured tessdata directory exists when provided."""
        if self.config.tesseract_data_path is None:
            return
        tessdata_path = Path(self.config.tesseract_data_path)
        if tessdata_path.exists() and tessdata_path.is_dir():
            return
        raise RuntimeError(
            "Configured tessdata directory does not exist: "
            f"{self.config.tesseract_data_path}"
        )
