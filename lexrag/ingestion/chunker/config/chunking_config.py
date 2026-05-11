"""Configuration contracts for the chunking package."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lexrag.ingestion.chunker.config.chunker_kind import ChunkerKind
from lexrag.ingestion.chunker.config.oversized_chunk_strategy import (
    OversizedChunkStrategy,
)

DEFAULT_RECURSIVE_SEPARATORS = (
    "\n\n",
    "\n",
    ". ",
    "? ",
    "! ",
    "; ",
    ", ",
    " ",
)


class ChunkingConfig(BaseModel):
    """Shared configuration for chunking orchestration and strategies."""

    model_config = ConfigDict(frozen=True)

    default_chunker: ChunkerKind = Field(default=ChunkerKind.SEMANTIC)
    min_chunk_tokens: int = Field(default=64, ge=1)
    target_chunk_tokens: int = Field(default=512, ge=1)
    max_chunk_tokens: int = Field(default=1024, ge=1)
    overlap_tokens: int = Field(default=96, ge=0)
    similarity_threshold: float = Field(default=0.72, ge=0.0, le=1.0)
    oversized_chunk_strategy: OversizedChunkStrategy = Field(
        default=OversizedChunkStrategy.RECURSIVE
    )
    recursive_separators: tuple[str, ...] = Field(
        default=DEFAULT_RECURSIVE_SEPARATORS
    )
    preserve_headings: bool = Field(default=True)
    low_quality_threshold: float = Field(default=0.40, ge=0.0, le=1.0)
    low_confidence_parse_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    low_confidence_ocr_threshold: float = Field(default=0.50, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_token_budget(self) -> ChunkingConfig:
        """Ensure token sizing and recursive splitting policies are coherent."""
        if self.min_chunk_tokens > self.target_chunk_tokens:
            raise ValueError("min_chunk_tokens must be <= target_chunk_tokens")
        if self.target_chunk_tokens > self.max_chunk_tokens:
            raise ValueError("target_chunk_tokens must be <= max_chunk_tokens")
        if self.overlap_tokens >= self.max_chunk_tokens:
            raise ValueError("overlap_tokens must be < max_chunk_tokens")
        if not self.recursive_separators:
            raise ValueError("recursive_separators must not be empty")
        return self
