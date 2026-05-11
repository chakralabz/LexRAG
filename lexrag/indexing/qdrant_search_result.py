"""Search-result record for in-memory Qdrant backend."""

from __future__ import annotations

from dataclasses import dataclass

from lexrag.ingestion.chunker.schemas.chunk import Chunk


@dataclass(slots=True)
class SearchResult:
    """Internal search result record for in-memory backend."""

    score: float
    chunk: Chunk
