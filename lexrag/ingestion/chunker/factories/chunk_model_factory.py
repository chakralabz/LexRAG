"""Factory that materializes canonical chunk models from builder payloads."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from datetime import date
from typing import Any

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.schemas.chunk_metadata import ChunkMetadata
from lexrag.ingestion.chunker.schemas.raw_chunk_payload import RawChunkPayload
from lexrag.ingestion.chunker.support.tokenization_engine import TokenizationEngine
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock
from lexrag.utils import get_logger

logger = get_logger(__name__)


class ChunkModelFactory:
    """Build stable chunk models with deterministic IDs and lineage metadata."""

    def __init__(
        self,
        *,
        tokenization_engine: TokenizationEngine | None = None,
    ) -> None:
        self.tokenization_engine = tokenization_engine or TokenizationEngine()

    def build_chunks(
        self,
        raw_chunks: Sequence[RawChunkPayload | dict[str, Any]],
        *,
        parsed_blocks: list[ParsedBlock],
    ) -> list[Chunk]:
        """Convert builder payloads into canonical chunk models."""
        if not raw_chunks:
            return []
        metadata_base = self._metadata_base(parsed_blocks=parsed_blocks)
        return self._build_all(
            raw_chunks=raw_chunks,
            parsed_blocks=parsed_blocks,
            metadata_base=metadata_base,
        )

    def _build_all(
        self,
        *,
        raw_chunks: Sequence[RawChunkPayload | dict[str, Any]],
        parsed_blocks: list[ParsedBlock],
        metadata_base: dict[str, Any],
    ) -> list[Chunk]:
        """Build all valid chunks for one document."""
        built_chunks: list[Chunk] = []
        for index, payload in enumerate(raw_chunks):
            chunk = self._build_chunk(
                payload=self._coerce_payload(payload=payload),
                index=index,
                total_chunks=len(raw_chunks),
                metadata_base=metadata_base,
            )
            if chunk is not None:
                built_chunks.append(chunk)
        return built_chunks

    def _coerce_payload(
        self,
        *,
        payload: RawChunkPayload | dict[str, Any],
    ) -> RawChunkPayload:
        """Normalize caller input to the typed raw payload schema."""
        if isinstance(payload, RawChunkPayload):
            return payload
        return RawChunkPayload.model_validate(payload)

    def _build_chunk(
        self,
        *,
        payload: RawChunkPayload,
        index: int,
        total_chunks: int,
        metadata_base: dict[str, Any],
    ) -> Chunk | None:
        """Build one canonical chunk or return None for invalid payloads."""
        text = payload.text.strip()
        if not text or not payload.source_blocks:
            return None
        chunk_id = payload.chunk_id or self._chunk_id(payload=payload, doc_id=metadata_base["doc_id"], text=text)
        metadata = self._metadata(
            payload=payload,
            index=index,
            total_chunks=total_chunks,
            metadata_base=metadata_base,
            text=text,
        )
        self._warn_on_boundary_artifact(text=text, chunk_id=chunk_id)
        return Chunk(
            chunk_id=chunk_id,
            text=text,
            embedding_text=None,
            metadata=metadata,
            embedding=None,
        )

    def _metadata(
        self,
        *,
        payload: RawChunkPayload,
        index: int,
        total_chunks: int,
        metadata_base: dict[str, Any],
        text: str,
    ) -> ChunkMetadata:
        """Build canonical metadata for one chunk payload."""
        payload_data = self._document_metadata(metadata_base=metadata_base)
        payload_data.update(
            self._chunk_position_metadata(
                payload=payload,
                first_block=payload.source_blocks[0],
                index=index,
                text=text,
                total_chunks=total_chunks,
            )
        )
        payload_data.update(self._quality_metadata(source_blocks=payload.source_blocks))
        payload_data["metadata"] = self._extension_metadata(payload=payload, text=text)
        return ChunkMetadata(**payload_data)

    def _document_metadata(self, *, metadata_base: dict[str, Any]) -> dict[str, Any]:
        """Build document-level metadata shared by all chunks."""
        return {
            "doc_id": metadata_base["doc_id"],
            "document_version": metadata_base["document_version"],
            "source_path": metadata_base["source_path"],
            "doc_type": metadata_base["doc_type"],
            "doc_date": metadata_base["doc_date"],
        }

    def _chunk_position_metadata(
        self,
        *,
        payload: RawChunkPayload,
        first_block: ParsedBlock,
        index: int,
        text: str,
        total_chunks: int,
    ) -> dict[str, Any]:
        """Build chunk-local positional and lineage metadata."""
        return {
            "chunk_index": index,
            "total_chunks": max(total_chunks, 1),
            "source_block_ids": [block.block_id for block in payload.source_blocks],
            "page_start": min(block.page for block in payload.source_blocks),
            "page_end": max(block.page for block in payload.source_blocks),
            "section_title": self._section_title(first_block=first_block, heading_anchor=payload.heading_anchor),
            "section_path": self._section_path(first_block=first_block),
            "heading_anchor": payload.heading_anchor,
            "chunk_type": payload.chunk_type,
            "chunking_strategy": payload.chunking_strategy,
            "token_count": payload.token_count or self.tokenization_engine.count_tokens(text),
            "char_count": len(text),
            "overlap_prev": payload.overlap_prev,
            "overlap_next": payload.overlap_next,
            "previous_chunk_id": payload.previous_chunk_id,
            "next_chunk_id": payload.next_chunk_id,
        }

    def _quality_metadata(self, *, source_blocks: list[ParsedBlock]) -> dict[str, Any]:
        """Build parser provenance and quality metadata."""
        return {
            "contains_table": any(block.block_type == "table" for block in source_blocks),
            "contains_code": any(block.block_type in {"code", "code_block"} for block in source_blocks),
            "contains_ocr": any(block.is_ocr for block in source_blocks),
            "avg_confidence": self._average_confidence(blocks=source_blocks),
            "parser_used": sorted({block.parser_used for block in source_blocks if block.parser_used}),
            "fallback_used": any(block.is_fallback_used for block in source_blocks),
            "ocr_used": any(bool(block.ocr_used) for block in source_blocks),
            "parse_confidence": self._parse_confidence(blocks=source_blocks),
        }

    def _metadata_base(self, *, parsed_blocks: list[ParsedBlock]) -> dict[str, Any]:
        """Resolve stable document-level defaults shared by all chunks."""
        if not parsed_blocks:
            return self._unknown_metadata()
        first = parsed_blocks[0]
        return {
            "doc_id": first.doc_id or "unknown_doc",
            "document_version": self._document_version(first.metadata),
            "source_path": first.source_path or "unknown_source",
            "doc_type": first.doc_type,
            "doc_date": self._normalize_doc_date(first.metadata.get("doc_date")),
        }

    def _unknown_metadata(self) -> dict[str, Any]:
        """Return safe metadata defaults for empty parsed block inputs."""
        return {
            "doc_id": "unknown_doc",
            "document_version": None,
            "source_path": "unknown_source",
            "doc_type": None,
            "doc_date": None,
        }

    def _chunk_id(self, *, payload: RawChunkPayload, doc_id: str, text: str) -> str:
        """Generate a deterministic chunk ID from block lineage and content."""
        source = "|".join(block.block_id for block in payload.source_blocks)
        digest = hashlib.sha1(f"{source}|{text[:500]}".encode()).hexdigest()[:12]
        page = min(block.page for block in payload.source_blocks)
        return f"{doc_id}_p{page}_{digest}"

    def _section_path(self, *, first_block: ParsedBlock) -> list[str]:
        """Build a safe section path for retrieval and citation lineage."""
        if first_block.parent_section_path:
            return [*first_block.parent_section_path, first_block.section]
        if first_block.section:
            return [first_block.section]
        return []

    def _section_title(
        self,
        *,
        first_block: ParsedBlock,
        heading_anchor: str | None,
    ) -> str | None:
        """Resolve a human-readable local section title."""
        if first_block.parent_section_path:
            for value in reversed(first_block.parent_section_path):
                if self._is_semantic_label(value):
                    return value.strip()
        if self._is_semantic_label(first_block.section):
            return first_block.section.strip()
        if heading_anchor and heading_anchor.strip():
            return self._humanize_anchor(heading_anchor)
        return first_block.section or None

    def _is_semantic_label(self, value: str | None) -> bool:
        """Return whether a label is useful to show to retrieval layers."""
        if not isinstance(value, str):
            return False
        return value.strip().lower() not in {"", "caption", "footnote", "paragraph", "table", "text"}

    def _humanize_anchor(self, value: str) -> str:
        """Convert a slug-like anchor into readable text."""
        compact = value.replace("_", " ").strip()
        compact = re.sub(r"(?<=\d)-(?=\d)", ".", compact)
        compact = compact.replace("-", " ")
        return re.sub(r"\s+", " ", compact).strip()

    def _parse_confidence(self, *, blocks: list[ParsedBlock]) -> float | None:
        """Average parse confidence when the parser emitted explicit scores."""
        values = [block.parse_confidence for block in blocks if block.parse_confidence is not None]
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    def _average_confidence(self, *, blocks: list[ParsedBlock]) -> float | None:
        """Average OCR confidence across source blocks when present."""
        values = [block.confidence for block in blocks if block.confidence is not None]
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    def _extension_metadata(
        self,
        *,
        payload: RawChunkPayload,
        text: str,
    ) -> dict[str, Any]:
        """Build extension metadata for audit and debugging workflows."""
        return {
            "heading_anchor": payload.heading_anchor,
            "is_fallback_used": any(block.is_fallback_used for block in payload.source_blocks),
            "source_spans": self._source_spans(text=text, source_blocks=payload.source_blocks),
            **self._fallback_provenance(source_blocks=payload.source_blocks),
        }

    def _fallback_provenance(
        self,
        *,
        source_blocks: list[ParsedBlock],
    ) -> dict[str, Any]:
        """Extract fallback parser provenance from source block metadata."""
        keys = {
            "fallback_event",
            "fallback_parser",
            "fallback_reason_code",
            "primary_error_message",
            "primary_error_type",
            "primary_parser",
        }
        for block in source_blocks:
            selected = {key: block.metadata[key] for key in keys if key in block.metadata}
            if selected:
                return selected
        return {}

    def _source_spans(
        self,
        *,
        text: str,
        source_blocks: list[ParsedBlock],
    ) -> list[dict[str, Any]]:
        """Locate approximate source spans for every contributing block."""
        spans: list[dict[str, Any]] = []
        cursor = 0
        for block in source_blocks:
            if not block.text.strip():
                continue
            start, end, match_type = self._locate_span(
                cursor=cursor,
                source_text=block.text.strip(),
                text=text,
            )
            spans.append(
                {
                    "block_id": block.block_id,
                    "page": block.page,
                    "start_char": start,
                    "end_char": end,
                    "matched": start is not None,
                    "match_type": match_type,
                }
            )
            if end is not None:
                cursor = end
        return spans

    def _locate_span(
        self,
        *,
        cursor: int,
        source_text: str,
        text: str,
    ) -> tuple[int | None, int | None, str]:
        """Match by exact text first and token anchor second."""
        exact_match = self._exact_span(cursor=cursor, source_text=source_text, text=text)
        if exact_match is not None:
            return (exact_match[0], exact_match[1], "exact")
        anchor_match = self._token_anchor_span(source_text=source_text, text=text)
        if anchor_match is not None:
            return (anchor_match[0], anchor_match[1], "token_anchor")
        return (None, None, "unmatched")

    def _exact_span(
        self,
        *,
        cursor: int,
        source_text: str,
        text: str,
    ) -> tuple[int, int] | None:
        """Find an exact character span with cursor-aware fallback search."""
        start = text.find(source_text, cursor)
        if start < 0:
            start = text.find(source_text)
        if start < 0:
            return None
        return (start, start + len(source_text))

    def _token_anchor_span(
        self,
        *,
        source_text: str,
        text: str,
    ) -> tuple[int, int] | None:
        """Fall back to a token anchor when the block text was reformatted."""
        source_tokens = self._token_positions(text=source_text)
        chunk_tokens = self._token_positions(text=text)
        if not source_tokens or not chunk_tokens:
            return None
        anchor_words = [token.lower() for token, _, _ in source_tokens[:4]]
        anchor_index = self._subsequence_index(
            haystack=[token.lower() for token, _, _ in chunk_tokens],
            needle=anchor_words,
        )
        if anchor_index is None:
            return None
        start = chunk_tokens[anchor_index][1]
        end = chunk_tokens[anchor_index + len(anchor_words) - 1][2]
        return (start, end)

    def _token_positions(self, *, text: str) -> list[tuple[str, int, int]]:
        """Extract alphanumeric tokens with source character offsets."""
        return [(match.group(0), match.start(), match.end()) for match in re.finditer(r"[A-Za-z0-9]+", text)]

    def _subsequence_index(
        self,
        *,
        haystack: list[str],
        needle: list[str],
    ) -> int | None:
        """Return the first position where a token sequence appears."""
        if not needle or len(needle) > len(haystack):
            return None
        limit = len(haystack) - len(needle)
        for start in range(limit + 1):
            if haystack[start : start + len(needle)] == needle:
                return start
        return None

    def _normalize_doc_date(self, value: Any) -> date | None:
        """Normalize persisted document dates to a date object."""
        if value is None or isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None
        return None

    def _document_version(self, metadata: dict[str, Any]) -> str | None:
        """Extract the stable document version when upstream parsing provided it."""
        value = metadata.get("document_version")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _warn_on_boundary_artifact(self, *, text: str, chunk_id: str) -> None:
        """Log likely boundary artifacts that deserve offline inspection."""
        stripped = text.lstrip()
        if stripped and stripped[0].islower():
            logger.warning(
                "Possible chunk boundary artifact detected for chunk_id=%s",
                chunk_id,
            )
