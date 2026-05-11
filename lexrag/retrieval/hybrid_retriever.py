"""Hybrid dense+sparse retrieval implementation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from lexrag.indexing.schemas import Chunk
from lexrag.retrieval.base import Retriever
from lexrag.retrieval.dense_retriever import DenseRetriever
from lexrag.retrieval.fusion import reciprocal_rank_fuse
from lexrag.retrieval.metadata import materialize_hits
from lexrag.retrieval.schemas import HybridRetrieverConfig, RetrievalHit
from lexrag.retrieval.sparse_retriever import SparseRetriever


class HybridRetriever(Retriever):
    """Fuse dense and sparse retrieval signals using reciprocal-rank fusion."""

    def __init__(
        self,
        *,
        dense_retriever: DenseRetriever,
        sparse_retriever: SparseRetriever,
        config: HybridRetrieverConfig | None = None,
    ) -> None:
        self.dense_retriever = dense_retriever
        self.sparse_retriever = sparse_retriever
        self.config = config or HybridRetrieverConfig()

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Return fused retrieval results with hybrid metadata attached."""

        hits = self.retrieve_hits(
            query,
            top_k=top_k,
            metadata_filters=metadata_filters,
        )
        return materialize_hits(hits, metadata_key="retrieval")

    def retrieve_hits(
        self,
        query: str,
        *,
        top_k: int | None = None,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[RetrievalHit]:
        """Return fused hits for reranking or direct response building."""

        limit = self._resolve_limit(top_k=top_k)
        dense_hits, sparse_hits = self._fetch_branch_hits(
            query=query,
            metadata_filters=metadata_filters,
        )
        fused_hits = reciprocal_rank_fuse(
            dense_hits=dense_hits,
            sparse_hits=sparse_hits,
            rrf_k=self.config.rrf_k,
            dense_weight=self.config.dense_weight,
            sparse_weight=self.config.sparse_weight,
        )
        return fused_hits[:limit]

    def _fetch_branch_hits(
        self,
        *,
        query: str,
        metadata_filters: dict[str, Any] | None,
    ) -> tuple[list[RetrievalHit], list[RetrievalHit]]:
        """Fetch dense and sparse candidates in parallel to reduce latency."""

        with ThreadPoolExecutor(max_workers=2) as executor:
            dense_future = executor.submit(
                self.dense_retriever.retrieve_hits,
                query,
                top_k=self.config.prefetch_k,
                metadata_filters=metadata_filters,
            )
            sparse_future = executor.submit(
                self.sparse_retriever.retrieve_hits,
                query,
                top_k=self.config.prefetch_k,
                metadata_filters=metadata_filters,
            )
            return dense_future.result(), sparse_future.result()

    def _resolve_limit(self, *, top_k: int | None) -> int:
        """Resolve and validate the requested result count."""

        if top_k is None:
            return self.config.top_k
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        return top_k
