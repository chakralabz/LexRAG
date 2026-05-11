"""Abstract reranker contract.

Rerankers operate strictly on retrieval outputs. They do not perform retrieval
themselves and they do not mutate indexes. This keeps retrieval, reranking, and
generation concerns separated along the architecture boundaries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from lexrag.indexing.schemas import Chunk


class Reranker(ABC):
    """Abstract reranker contract."""

    @abstractmethod
    def rerank(
        self, query: str, chunks: list[Chunk], *, top_k: int | None = None
    ) -> list[Chunk]:
        """Return a reranked subset of the supplied chunks.

        Args:
            query: End-user query string.
            chunks: Candidate chunks already produced by a retriever.
            top_k: Optional override for the number of reranked chunks returned.

        Returns:
            A ranked subset of the input chunks.
        """
