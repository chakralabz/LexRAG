"""Common retrieval contracts.

The retrieval package intentionally exposes a minimal interface because the rest
of the system should depend only on the ability to retrieve ranked chunks for a
query. Dense, sparse, and hybrid implementations remain interchangeable behind
this contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lexrag.indexing.schemas import Chunk


class Retriever(ABC):
    """Abstract retrieval contract shared by all retrieval strategies."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Return ranked chunks for the supplied query.

        Args:
            query: End-user query string.
            top_k: Optional override for the number of chunks returned.
            metadata_filters: Optional query-time filters applied before final
                ranking. Implementations may delegate backend-safe clauses to
                storage and evaluate richer clauses in memory.

        Returns:
            Ranked chunks suitable for reranking or direct context-building.
        """
