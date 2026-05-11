"""Sparse retrieval implementation."""

from __future__ import annotations

from typing import Any

from lexrag.indexing.bm25_store import BM25Store
from lexrag.indexing.schemas import Chunk
from lexrag.retrieval.base import Retriever
from lexrag.retrieval.filtering import matches_residual_filters, split_backend_filters
from lexrag.retrieval.metadata import materialize_hits
from lexrag.retrieval.schemas import RetrievalHit, SparseRetrieverConfig


class SparseRetriever(Retriever):
    """Query the lexical index while keeping filter semantics consistent."""

    def __init__(
        self,
        *,
        store: BM25Store,
        config: SparseRetrieverConfig | None = None,
    ) -> None:
        self.store = store
        self.config = config or SparseRetrieverConfig()

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Return sparse-retrieval results with query-time metadata attached."""

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
        """Return scored sparse hits for downstream fusion or reranking."""

        normalized_query = query.strip()
        if not normalized_query:
            return []
        limit = self._resolve_limit(top_k=top_k)
        backend_filters, residual_filters = split_backend_filters(metadata_filters)
        candidates = self.store.search_bm25(
            normalized_query,
            limit=max(limit, self.config.candidate_pool_size),
            metadata_filters=backend_filters,
        )
        return self._rank_candidates(
            candidates=candidates,
            limit=limit,
            residual_filters=residual_filters,
        )

    def _rank_candidates(
        self,
        *,
        candidates: list[Chunk],
        limit: int,
        residual_filters: dict[str, dict[str, Any]],
    ) -> list[RetrievalHit]:
        """Emit stable hit records from backend-ranked sparse results."""

        filtered = [
            chunk
            for chunk in candidates
            if matches_residual_filters(chunk, residual_filters)
        ]
        return [
            RetrievalHit(
                chunk=chunk,
                score=1.0 / position,
                source="sparse",
                rank=position,
                branch_scores={"sparse_score": 1.0 / position},
            )
            for position, chunk in enumerate(filtered[:limit], start=1)
        ]

    def _resolve_limit(self, *, top_k: int | None) -> int:
        """Resolve and validate the requested result count."""

        if top_k is None:
            return self.config.top_k
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        return top_k
