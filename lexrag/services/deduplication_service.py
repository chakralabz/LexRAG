"""Public deduplication service for block and vector reuse."""

from __future__ import annotations

from lexrag.indexing.schemas import Chunk
from lexrag.ingestion.deduplicator import BlockDeduplicator
from lexrag.ingestion.parser import ParsedBlock
from lexrag.vector.vector_deduplicator import VectorDeduplicator


class DeduplicationService:
    """Deduplicate intermediate parser blocks and final chunk vectors."""

    def __init__(
        self,
        *,
        block_deduplicator: BlockDeduplicator | None = None,
        vector_deduplicator: VectorDeduplicator | None = None,
    ) -> None:
        self._block_deduplicator = block_deduplicator or BlockDeduplicator()
        self._vector_deduplicator = vector_deduplicator or VectorDeduplicator()

    def deduplicate_blocks(self, blocks: list[ParsedBlock]) -> list[ParsedBlock]:
        """Remove redundant parsed blocks while preserving order."""
        return self._block_deduplicator.deduplicate(blocks)

    def deduplicate_vectors(self, chunks: list[Chunk]) -> list[Chunk]:
        """Remove semantically redundant embedded chunks."""
        return self._vector_deduplicator.deduplicate(chunks)
