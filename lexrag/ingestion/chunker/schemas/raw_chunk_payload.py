"""Intermediate payload emitted by chunk builders before model materialization."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.ingestion.chunker.config.chunk_type import ChunkType
from lexrag.ingestion.chunker.config.chunking_strategy import ChunkingStrategy
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class RawChunkPayload(BaseModel):
    """Carries builder output prior to canonical chunk model creation.

    The factory turns this payload into a stable, validated `Chunk`. Keeping
    this schema explicit makes it possible to test builder behavior without
    coupling those tests to indexing metadata or vector store requirements.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    text: str = Field(description="Chunk display text.")
    source_blocks: list[ParsedBlock] = Field(default_factory=list)
    chunking_strategy: ChunkingStrategy = Field(
        description="Strategy used to form the chunk."
    )
    chunk_type: ChunkType = Field(
        default=ChunkType.PARAGRAPH,
        description="Dominant block type.",
    )
    token_count: int | None = Field(default=None, ge=0)
    overlap_prev: bool = Field(default=False)
    overlap_next: bool = Field(default=False)
    previous_chunk_id: str | None = Field(default=None)
    next_chunk_id: str | None = Field(default=None)
    heading_anchor: str | None = Field(default=None)
    chunk_id: str | None = Field(default=None)
