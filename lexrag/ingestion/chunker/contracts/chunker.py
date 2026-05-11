"""Chunker contract for ingestion-layer segmentation strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class Chunker(ABC):
    """Contract for all chunker implementations."""

    @abstractmethod
    def chunk(self, blocks: list[ParsedBlock]) -> list[Chunk]:
        """Build retrieval chunks from normalized parsed blocks."""
