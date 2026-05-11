"""Canonical schemas for the chunking layer.

The chunker package sits between normalized parsed blocks and indexing-ready
chunks. Keeping its contracts in a dedicated schema package avoids circular
imports, clarifies ownership, and makes it safe for downstream packages to
depend on these models without importing builder/planner logic.
"""

from __future__ import annotations

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.schemas.chunk_metadata import ChunkMetadata
from lexrag.ingestion.chunker.schemas.chunking_config import ChunkingConfig
from lexrag.ingestion.chunker.schemas.planned_chunk import PlannedChunk
from lexrag.ingestion.chunker.schemas.raw_chunk_payload import RawChunkPayload
from lexrag.ingestion.chunker.schemas.token_context import TokenContext

__all__ = [
    "Chunk",
    "ChunkMetadata",
    "ChunkingConfig",
    "PlannedChunk",
    "RawChunkPayload",
    "TokenContext",
]
