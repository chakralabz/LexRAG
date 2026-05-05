"""Typed configuration surface for chunking."""

from lexrag.ingestion.chunker.config.chunk_type import ChunkType
from lexrag.ingestion.chunker.config.chunker_kind import ChunkerKind
from lexrag.ingestion.chunker.config.chunking_config import ChunkingConfig
from lexrag.ingestion.chunker.config.chunking_strategy import ChunkingStrategy
from lexrag.ingestion.chunker.config.oversized_chunk_strategy import (
    OversizedChunkStrategy,
)

__all__ = [
    "ChunkType",
    "ChunkerKind",
    "ChunkingConfig",
    "ChunkingStrategy",
    "OversizedChunkStrategy",
]
