"""Compatibility wrapper for the architecture-aligned block deduplicator."""

from __future__ import annotations

from lexrag.ingestion.deduplicator.block_deduplicator import BlockDeduplicator
from lexrag.ingestion.deduplicator.schemas import BlockDeduplicationConfig
from lexrag.ingestion.deduplicator.similarity_engine import SimilarityEngine


class MinHashDeduplicator(BlockDeduplicator):
    """Backwards-compatible entry point for near-duplicate block suppression."""

    def __init__(
        self,
        *,
        threshold: float = 0.95,
        similarity_engine: SimilarityEngine | None = None,
    ) -> None:
        super().__init__(
            config=BlockDeduplicationConfig(near_duplicate_threshold=threshold),
            similarity_engine=similarity_engine,
        )
