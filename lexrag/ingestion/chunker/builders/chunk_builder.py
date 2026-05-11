"""Chunk builder that materializes raw payloads from planner output."""

from __future__ import annotations

import re

from lexrag.ingestion.chunker.config.chunk_type import ChunkType
from lexrag.ingestion.chunker.config.chunking_config import ChunkingConfig
from lexrag.ingestion.chunker.config.chunking_strategy import ChunkingStrategy
from lexrag.ingestion.chunker.schemas.planned_chunk import PlannedChunk
from lexrag.ingestion.chunker.schemas.raw_chunk_payload import RawChunkPayload
from lexrag.ingestion.chunker.support.recursive_text_splitter import (
    RecursiveTextSplitter,
)
from lexrag.ingestion.chunker.support.similarity_engine import SimilarityEngine
from lexrag.ingestion.chunker.support.tokenization_engine import TokenizationEngine
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class ChunkBuilder:
    """Build raw chunk payloads from explicit planner output."""

    def __init__(
        self,
        *,
        config: ChunkingConfig | None = None,
        tokenization_engine: TokenizationEngine | None = None,
        similarity_engine: SimilarityEngine | None = None,
        recursive_text_splitter: RecursiveTextSplitter | None = None,
    ) -> None:
        self.config = config or ChunkingConfig()
        self.tokenization_engine = tokenization_engine or TokenizationEngine()
        self.similarity_engine = similarity_engine or SimilarityEngine()
        self.recursive_text_splitter = recursive_text_splitter or self._splitter()

    def build(self, plans: list[PlannedChunk]) -> list[RawChunkPayload]:
        """Convert planner records into ordered raw chunk payloads."""
        raw_chunks: list[RawChunkPayload] = []
        buffer: list[PlannedChunk] = []
        current_anchor: str | None = None
        for plan in plans:
            current_anchor = self._apply_plan(
                plan=plan,
                buffer=buffer,
                raw_chunks=raw_chunks,
                current_anchor=current_anchor,
            )
        self._flush_buffer(buffer=buffer, raw_chunks=raw_chunks, heading_anchor=current_anchor)
        self._mark_adjacency(raw_chunks=raw_chunks)
        return raw_chunks

    def _apply_plan(
        self,
        *,
        plan: PlannedChunk,
        buffer: list[PlannedChunk],
        raw_chunks: list[RawChunkPayload],
        current_anchor: str | None,
    ) -> str | None:
        """Process one planner record and return the active heading anchor."""
        if plan.chunking_strategy == ChunkingStrategy.HEADING_ANCHORED:
            self._flush_buffer(buffer=buffer, raw_chunks=raw_chunks, heading_anchor=current_anchor)
            return plan.heading_anchor or plan.text
        if plan.chunking_strategy in self._windowed_strategies():
            self._flush_buffer(buffer=buffer, raw_chunks=raw_chunks, heading_anchor=current_anchor)
            raw_chunks.extend(self._oversized_chunks(plan=plan, heading_anchor=current_anchor))
            return current_anchor
        if plan.standalone:
            self._flush_buffer(buffer=buffer, raw_chunks=raw_chunks, heading_anchor=current_anchor)
            raw_chunks.append(self._standalone_chunk(plan=plan, heading_anchor=current_anchor))
            return current_anchor
        if self._should_flush(buffer=buffer, incoming=plan):
            self._flush_buffer(buffer=buffer, raw_chunks=raw_chunks, heading_anchor=current_anchor)
        buffer.append(plan)
        return current_anchor or plan.heading_anchor

    def _should_flush(
        self,
        *,
        buffer: list[PlannedChunk],
        incoming: PlannedChunk,
    ) -> bool:
        """Determine whether the incoming plan should start a new chunk."""
        if not buffer:
            return False
        if incoming.section_boundary:
            return True
        if self._buffer_tokens(buffer=buffer) + incoming.token_count > self.config.max_chunk_tokens:
            return True
        if self._buffer_tokens(buffer=buffer) < self.config.min_chunk_tokens:
            return False
        similarity = self.similarity_engine.score_text_pair(buffer[-1].text, incoming.text)
        return similarity < self.config.similarity_threshold

    def _flush_buffer(
        self,
        *,
        buffer: list[PlannedChunk],
        raw_chunks: list[RawChunkPayload],
        heading_anchor: str | None,
    ) -> None:
        """Materialize buffered plans into a merged semantic payload."""
        if buffer:
            raw_chunks.append(self._merged_chunk(plans=list(buffer), heading_anchor=heading_anchor))
            buffer.clear()

    def _merged_chunk(
        self,
        *,
        plans: list[PlannedChunk],
        heading_anchor: str | None,
    ) -> RawChunkPayload:
        """Build one semantic-merge payload from buffered plans."""
        blocks = [plan.block for plan in plans]
        return RawChunkPayload(
            text=self._compose_text(
                body_parts=[plan.text for plan in plans],
                source_blocks=blocks,
                heading_anchor=heading_anchor,
            ),
            source_blocks=blocks,
            chunking_strategy=ChunkingStrategy.SEMANTIC_MERGE,
            chunk_type=self._chunk_type(blocks=blocks),
            token_count=sum(plan.token_count for plan in plans),
            heading_anchor=heading_anchor,
        )

    def _standalone_chunk(
        self,
        *,
        plan: PlannedChunk,
        heading_anchor: str | None,
    ) -> RawChunkPayload:
        """Build a protected standalone chunk for isolated block types."""
        return RawChunkPayload(
            text=self._compose_text(
                body_parts=[plan.text],
                source_blocks=[plan.block],
                heading_anchor=heading_anchor,
            ),
            source_blocks=[plan.block],
            chunking_strategy=plan.chunking_strategy,
            chunk_type=self._normalized_block_type(plan.block.block_type),
            token_count=plan.token_count,
            heading_anchor=heading_anchor,
        )

    def _oversized_chunks(
        self,
        *,
        plan: PlannedChunk,
        heading_anchor: str | None,
    ) -> list[RawChunkPayload]:
        """Split one oversized block into configured window chunks."""
        if plan.chunking_strategy == ChunkingStrategy.RECURSIVE_WINDOW:
            return self._recursive_chunks(plan=plan, heading_anchor=heading_anchor)
        return self._sliding_window_chunks(plan=plan, heading_anchor=heading_anchor)

    def _recursive_chunks(
        self,
        *,
        plan: PlannedChunk,
        heading_anchor: str | None,
    ) -> list[RawChunkPayload]:
        """Chunk oversized text with semantic recursive separators."""
        parts = self.recursive_text_splitter.split(plan.text)
        return self._payloads_from_parts(
            parts=parts,
            strategy=ChunkingStrategy.RECURSIVE_WINDOW,
            plan=plan,
            heading_anchor=heading_anchor,
        )

    def _sliding_window_chunks(
        self,
        *,
        plan: PlannedChunk,
        heading_anchor: str | None,
    ) -> list[RawChunkPayload]:
        """Chunk oversized text with overlapping token windows."""
        tokens = self.tokenization_engine.tokenize(plan.text)
        windows = self.tokenization_engine.window_tokens(
            tokens=tokens,
            window_size=self.config.target_chunk_tokens,
            overlap=self.config.overlap_tokens,
        )
        parts = [self.tokenization_engine.detokenize(window) for window in windows]
        return self._payloads_from_parts(
            parts=parts,
            strategy=ChunkingStrategy.SLIDING_WINDOW,
            plan=plan,
            heading_anchor=heading_anchor,
        )

    def _payloads_from_parts(
        self,
        *,
        parts: list[str],
        strategy: ChunkingStrategy,
        plan: PlannedChunk,
        heading_anchor: str | None,
    ) -> list[RawChunkPayload]:
        """Build raw payloads from already-split oversized text parts."""
        return [
            RawChunkPayload(
                text=self._compose_text(
                    body_parts=[part],
                    source_blocks=[plan.block],
                    heading_anchor=heading_anchor,
                ),
                source_blocks=[plan.block],
                chunking_strategy=strategy,
                chunk_type=self._normalized_block_type(plan.block.block_type),
                token_count=self.tokenization_engine.count_tokens(part),
                heading_anchor=heading_anchor,
            )
            for part in parts
        ]

    def _mark_adjacency(self, *, raw_chunks: list[RawChunkPayload]) -> None:
        """Mark boolean overlap adjacency for downstream compatibility."""
        for index, payload in enumerate(raw_chunks):
            payload.overlap_prev = index > 0
            payload.overlap_next = index < len(raw_chunks) - 1

    def _compose_text(
        self,
        *,
        body_parts: list[str],
        source_blocks: list[ParsedBlock],
        heading_anchor: str | None,
    ) -> str:
        """Prepend heading context once so chunks remain retrieval-safe."""
        parts = [part.strip() for part in body_parts if part.strip()]
        heading = self._display_heading(source_blocks=source_blocks, heading_anchor=heading_anchor)
        if self.config.preserve_headings and heading and parts and parts[0] != heading:
            parts.insert(0, heading)
        return "\n\n".join(parts).strip()

    def _display_heading(
        self,
        *,
        source_blocks: list[ParsedBlock],
        heading_anchor: str | None,
    ) -> str | None:
        """Resolve human-readable heading context for display text."""
        if source_blocks:
            label = self._section_label(block=source_blocks[0])
            if label:
                return label
        if heading_anchor:
            return self._humanize_anchor(heading_anchor)
        return None

    def _section_label(self, *, block: ParsedBlock) -> str | None:
        """Prefer semantic section labels over parser-generic placeholders."""
        lineage = [part.strip() for part in block.parent_section_path if self._is_semantic_label(part)]
        if lineage:
            return lineage[-1]
        if self._is_semantic_label(block.section):
            return block.section.strip()
        return None

    def _is_semantic_label(self, value: str | None) -> bool:
        """Return whether a section label carries retrieval value."""
        if not isinstance(value, str):
            return False
        return value.strip().lower() not in {"", "caption", "footnote", "paragraph", "table", "text"}

    def _humanize_anchor(self, value: str) -> str:
        """Convert slug-like anchors into readable section labels."""
        compact = value.replace("_", " ").strip()
        compact = re.sub(r"(?<=\d)-(?=\d)", ".", compact)
        compact = compact.replace("-", " ")
        return re.sub(r"\s+", " ", compact).strip()

    def _buffer_tokens(self, *, buffer: list[PlannedChunk]) -> int:
        """Return total token count for buffered planner records."""
        return sum(plan.token_count for plan in buffer)

    def _chunk_type(self, *, blocks: list[ParsedBlock]) -> ChunkType:
        """Resolve a stable chunk type from source block composition."""
        types = {self._normalized_block_type(block.block_type) for block in blocks if block.block_type}
        if ChunkType.TABLE in types:
            return ChunkType.TABLE
        if ChunkType.CODE in types:
            return ChunkType.CODE
        if ChunkType.LIST in types:
            return ChunkType.LIST
        return ChunkType.PARAGRAPH

    def _normalized_block_type(self, block_type: str | None) -> ChunkType:
        """Normalize parser block types to architecture-level chunk types."""
        if block_type in {None, "", "paragraph"}:
            return ChunkType.PARAGRAPH
        if block_type in {"code", "code_block"}:
            return ChunkType.CODE
        if block_type == "list":
            return ChunkType.LIST
        if block_type == "definition":
            return ChunkType.DEFINITION
        if block_type in {"caption", "image", "image_caption", "table_caption"}:
            return ChunkType.IMAGE
        if block_type == "table":
            return ChunkType.TABLE
        return ChunkType.PARAGRAPH

    def _windowed_strategies(self) -> set[ChunkingStrategy]:
        """Return strategies that split oversized blocks into subchunks."""
        return {ChunkingStrategy.RECURSIVE_WINDOW, ChunkingStrategy.SLIDING_WINDOW}

    def _splitter(self) -> RecursiveTextSplitter:
        """Build the recursive splitter used for oversized semantic blocks."""
        return RecursiveTextSplitter(
            tokenization_engine=self.tokenization_engine,
            separators=self.config.recursive_separators,
            min_tokens=self.config.min_chunk_tokens,
            target_tokens=self.config.target_chunk_tokens,
            max_tokens=self.config.max_chunk_tokens,
            overlap_tokens=self.config.overlap_tokens,
        )
