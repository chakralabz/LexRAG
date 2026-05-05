"""Canonical metadata schema for indexing-ready chunks."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from lexrag.ingestion.chunker.config.chunk_type import ChunkType
from lexrag.ingestion.chunker.config.chunking_strategy import ChunkingStrategy


class ChunkMetadata(BaseModel):
    """Audit-safe metadata attached to every chunk.

    Attributes:
        doc_id: Stable document identifier used across retrieval and indexing.
        document_version: Source version label preserved for re-index safety.
        source_path: Original source path captured for audits and debugging.
        doc_type: High-level document family for retrieval filters.
        doc_date: Source publication or effective date when available.
        chunk_index: Zero-based chunk position within the document.
        total_chunks: Total chunk count for the source document.
        source_block_ids: Ordered parser block lineage used to build the chunk.
        page_start: First contributing page.
        page_end: Last contributing page.
        section_title: Local section title for rendering and retrieval.
        section_path: Full heading ancestry for the chunk.
        heading_anchor: Stable anchor-friendly section label.
        chunk_type: Chunk classification such as paragraph or table.
        chunking_strategy: Strategy label used to build the chunk.
        token_count: Token count for the retrieval-facing chunk text.
        char_count: Character count for the retrieval-facing chunk text.
        overlap_prev: Whether the chunk overlaps with its predecessor.
        overlap_next: Whether the chunk overlaps with its successor.
        previous_chunk_id: Previous chunk ID when overlap is present.
        next_chunk_id: Next chunk ID when overlap is present.
        contains_table: Whether source content contains a table.
        contains_code: Whether source content contains code.
        contains_ocr: Whether OCR contributed to the chunk.
        avg_confidence: Aggregate parser/OCR confidence signal.
        parser_used: Ordered parser names that touched contributing blocks.
        fallback_used: Whether a parser fallback path executed.
        ocr_used: Whether OCR was required.
        parse_confidence: Parser confidence score in `[0, 1]`.
        chunk_quality_score: Post-processing quality score in `[0, 1]`.
        ingestion_timestamp: UTC ingestion timestamp for the chunk.
        embedding_model: Embedding model name used for vector generation.
        embedding_model_version: Pinned embedding model version.
        reranker_score: Retrieval-time reranker score when available.
        citation_confidence: Citation resolver confidence when available.
        metadata: Extension payload reserved for layer-specific metadata.

    The architecture requires chunks to preserve section lineage, parser
    provenance, and overlap context. This model is the contract that makes that
    information portable across indexing, retrieval, and evaluation layers.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    doc_id: str | None = Field(default=None)
    document_version: str | None = Field(default=None)
    source_path: str | None = Field(default=None)
    doc_type: str | None = Field(default=None)
    doc_date: date | None = Field(default=None)
    chunk_index: int = Field(ge=0)
    total_chunks: int = Field(ge=1)
    source_block_ids: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("source_block_ids", "source_blocks"),
    )
    page_start: int = Field(
        default=1,
        ge=1,
        validation_alias=AliasChoices("page_start", "page_num"),
    )
    page_end: int = Field(
        default=1,
        ge=1,
        validation_alias=AliasChoices("page_end", "page_num"),
    )
    section_title: str | None = Field(default=None)
    section_path: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("section_path", "parent_section_path"),
    )
    heading_anchor: str | None = Field(default=None)
    chunk_type: ChunkType = Field(default=ChunkType.PARAGRAPH)
    chunking_strategy: ChunkingStrategy = Field(default=ChunkingStrategy.UNSPECIFIED)
    token_count: int | None = Field(default=None, ge=0)
    char_count: int | None = Field(default=None, ge=0)
    overlap_prev: bool = Field(default=False)
    overlap_next: bool = Field(default=False)
    previous_chunk_id: str | None = Field(default=None)
    next_chunk_id: str | None = Field(default=None)
    contains_table: bool = Field(default=False)
    contains_code: bool = Field(default=False)
    contains_ocr: bool = Field(default=False)
    avg_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    parser_used: list[str] = Field(default_factory=list)
    fallback_used: bool = Field(default=False)
    ocr_used: bool = Field(default=False)
    parse_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    chunk_quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    ingestion_timestamp: datetime | None = Field(default=None)
    embedding_model: str | None = Field(default=None)
    embedding_model_version: str | None = Field(default=None)
    reranker_score: float | None = Field(default=None)
    citation_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def page_num(self) -> int:
        """Returns the start page for legacy single-page callers."""
        return self.page_start

    @property
    def parent_section_path(self) -> list[str]:
        """Provides a backward-compatible alias for older metadata readers."""
        return self.section_path
