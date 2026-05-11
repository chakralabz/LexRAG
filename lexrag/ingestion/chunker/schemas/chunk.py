"""Canonical chunk schema shared across ingestion, indexing, and retrieval."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.ingestion.chunker.schemas.chunk_metadata import ChunkMetadata


class Chunk(BaseModel):
    """Retrieval-safe content unit created by the chunking pipeline."""

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    chunk_id: str = Field(
        pattern=r"^(?:[A-Za-z0-9]+|[A-Za-z0-9][A-Za-z0-9._-]*_[A-Za-z0-9._-]+)$"
    )
    text: str = Field(description="Chunk display text.")
    embedding_text: str | None = Field(default=None)
    metadata: ChunkMetadata = Field(description="Canonical chunk metadata.")
    embedding: list[float] | None = Field(default=None)
