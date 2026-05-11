"""Stable parser backend identifiers."""

from __future__ import annotations

from enum import StrEnum


class ParserBackend(StrEnum):
    """Enumerate the parser backends known to orchestration."""

    DOCLING = "docling"
    PYMUPDF = "pymupdf"
    UNSTRUCTURED = "unstructured"
    OCR_ONLY = "ocr_only"
    MANUAL_RECOVERY = "manual_recovery"
