"""Public chunking service for SDK consumers."""

from __future__ import annotations

from lexrag.indexing.schemas import Chunk
from lexrag.ingestion.chunker import Chunker, FixedSizeChunker
from lexrag.ingestion.parser import ParsedBlock


class ChunkingService:
    """Turn normalized blocks into canonical retrieval chunks."""

    def __init__(self, *, chunker: Chunker | None = None) -> None:
        self._chunker = chunker or FixedSizeChunker()

    def chunk(self, blocks: list[ParsedBlock]) -> list[Chunk]:
        """Chunk one normalized document into canonical chunk objects."""
        return self._chunker.chunk(blocks)
