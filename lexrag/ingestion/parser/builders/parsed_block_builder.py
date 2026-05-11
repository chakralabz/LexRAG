"""Shared builder for canonical parsed blocks.

The parser package has several backend adapters that all need to emit the same
``ParsedBlock`` shape. Centralizing that logic keeps backend implementations
focused on extraction instead of repeating metadata and identifier wiring.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class ParsedBlockBuilder:
    """Build canonical parsed blocks with stable source metadata."""

    def build(
        self,
        *,
        path: Path,
        parser_name: str,
        page: int,
        section: str,
        text: str,
        order_in_page: int,
        block_type: str = "paragraph",
        markdown: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        heading_level: int | None = None,
        is_ocr: bool = False,
        confidence: float | None = None,
        ocr_used: str | None = None,
        parse_confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ParsedBlock:
        """Build one canonical parsed block.

        Args:
            path: Source document path.
            parser_name: Stable parser backend identifier.
            page: One-based page number.
            section: Human-readable section label.
            text: Extracted plain text.
            order_in_page: Stable order within the page.
            block_type: Normalized block type.
            markdown: Optional markdown rendering for the block.
            bbox: Optional source-space bounding box.
            heading_level: Optional heading depth.
            is_ocr: Whether OCR produced the content.
            confidence: Backend confidence when available.
            ocr_used: OCR backend identifier when applicable.
            parse_confidence: Final parse confidence when already known.
            metadata: Additional backend-specific metadata.

        Returns:
            Fully populated ``ParsedBlock``.
        """
        normalized_text = text.strip()
        normalized_markdown = markdown.strip() if markdown is not None else None
        return ParsedBlock(
            doc_id=path.stem,
            source_path=str(path),
            source_name=path.name,
            doc_type=path.suffix.lower().lstrip(".") or None,
            block_id=self._build_block_id(
                path=path,
                page=page,
                order=order_in_page,
                text=normalized_text,
            ),
            page=page,
            section=section.strip() or f"Page {page}",
            heading_level=heading_level,
            block_type=block_type,
            text=normalized_text,
            markdown=normalized_markdown or normalized_text,
            bbox=bbox,
            order_in_page=order_in_page,
            is_ocr=is_ocr,
            confidence=confidence,
            parser_used=parser_name,
            ocr_used=ocr_used,
            parse_confidence=parse_confidence,
            metadata=dict(metadata or {}),
        )

    def _build_block_id(self, *, path: Path, page: int, order: int, text: str) -> str:
        """Build deterministic block identifiers from stable source attributes."""
        digest = hashlib.sha1(text[:500].encode("utf-8")).hexdigest()[:12]
        return f"{path.stem}_p{page}_b{order}_{digest}"
