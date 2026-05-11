"""Abstract OCR extraction contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from lexrag.ingestion.parser.schemas.ocr_text_block import OCRTextBlock


class OCRExtractor(ABC):
    """Extract OCR text blocks from raster images."""

    @abstractmethod
    def extract(self, *, image_path: Path, page_number: int) -> list[OCRTextBlock]:
        """Return OCR text blocks for one rasterized page image."""
