"""Factories for canonical parsed block creation.

This module is the compatibility layer between modern parser backends that
already emit `ParsedBlock` and older code paths that still return lightweight
dictionaries or ad-hoc objects.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexrag.ingestion.parser.builders.parsed_block_builder import ParsedBlockBuilder
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class ParsedBlockFactory:
    """Coerce legacy and backend-specific payloads into ``ParsedBlock``."""

    def __init__(self, builder: ParsedBlockBuilder | None = None) -> None:
        """Initialize the canonical block builder used for normalization."""
        self.builder = builder or ParsedBlockBuilder()

    def build_blocks(
        self,
        *,
        path: Path,
        parser_name: str,
        parsed_items: list[Any],
    ) -> list[ParsedBlock]:
        """Normalize backend outputs into canonical parsed blocks.

        Args:
            path: Source document path.
            parser_name: Stable parser name used for provenance.
            parsed_items: Backend output objects to normalize.

        Returns:
            Canonical parsed blocks with deterministic identity.
        """
        normalized: list[ParsedBlock] = []
        for index, item in enumerate(parsed_items, start=1):
            # Ordering is preserved because downstream chunking can use emitted
            # order as a tie-breaker when multiple blocks share a page number.
            normalized.append(
                self._coerce_item(
                    path=path,
                    parser_name=parser_name,
                    item=item,
                    index=index,
                )
            )
        return normalized

    def _coerce_item(
        self,
        *,
        path: Path,
        parser_name: str,
        item: Any,
        index: int,
    ) -> ParsedBlock:
        """Convert a backend item into the shared block schema."""
        if isinstance(item, ParsedBlock):
            return self._enrich_parsed_block(
                path=path, parser_name=parser_name, item=item
            )
        # Legacy backends often return dict payloads while older DTO-style
        # adapters expose attributes. We normalize both into one payload shape.
        payload = item if isinstance(item, dict) else self._object_to_payload(item=item)
        return self._build_block_from_payload(
            path=path,
            parser_name=parser_name,
            payload=payload,
            index=index,
        )

    def _enrich_parsed_block(
        self,
        *,
        path: Path,
        parser_name: str,
        item: ParsedBlock,
    ) -> ParsedBlock:
        """Backfill required provenance fields on existing parsed blocks."""
        # Existing ParsedBlock instances may already contain rich backend
        # metadata, so we only fill missing identity/provenance fields.
        updates = {
            "doc_id": item.doc_id or path.stem,
            "source_path": item.source_path or str(path),
            "source_name": item.source_name or path.name,
            "doc_type": item.doc_type or path.suffix.lower().lstrip(".") or None,
            "parser_used": item.parser_used or parser_name,
        }
        return item.model_copy(update=updates)

    def _build_block_from_payload(
        self,
        *,
        path: Path,
        parser_name: str,
        payload: dict[str, Any],
        index: int,
    ) -> ParsedBlock:
        """Build a parsed block from a generic payload."""
        text = str(payload.get("text", "")).strip()
        page = self._resolve_page(value=payload.get("page"), fallback=index)
        section = str(payload.get("section", f"Page {page}")).strip() or f"Page {page}"
        metadata = dict(payload.get("metadata", {}) or {})
        return self.builder.build(
            path=path,
            parser_name=parser_name,
            page=page,
            section=section,
            text=text,
            order_in_page=index,
            metadata=metadata,
        )

    def _object_to_payload(self, *, item: Any) -> dict[str, Any]:
        """Extract a generic payload from legacy parser DTOs."""
        return {
            "page": getattr(item, "page", None),
            "section": getattr(item, "section", None),
            "text": getattr(item, "text", None),
            "metadata": getattr(item, "metadata", {}) or {},
        }

    def _resolve_page(self, *, value: Any, fallback: int) -> int:
        """Normalize page values into safe 1-based integers."""
        try:
            page = int(value)
        except (TypeError, ValueError):
            return max(fallback, 1)
        return page if page >= 1 else max(fallback, 1)
