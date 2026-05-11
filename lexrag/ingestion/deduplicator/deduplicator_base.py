"""Abstract contract for the block-level deduplication layer.

The architecture places deduplication after normalization and before block
quality validation. This contract intentionally operates on ``ParsedBlock``
objects so the layer can make provenance-aware decisions without depending on
chunking or indexing internals.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class Deduplicator(ABC):
    """Contract for services that remove redundant parsed blocks."""

    @abstractmethod
    def deduplicate(self, blocks: list[ParsedBlock]) -> list[ParsedBlock]:
        """Return an ordered block list with duplicates removed.

        Args:
            blocks: Normalized parsed blocks for a single document stream.

        Returns:
            The subset of blocks that should continue to validation and
            chunking, preserving the first retained occurrence of each concept.
        """
