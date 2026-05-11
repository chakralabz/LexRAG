"""Dense retrieval implementation."""

from __future__ import annotations

from typing import Any

from lexrag.indexing.backends.vector_math import cosine_similarity
from lexrag.vector.qdrant_store import QdrantStore
from lexrag.indexing.schemas import Chunk
from lexrag.ingestion.embedder import BGEEmbedder
from lexrag.retrieval.base import Retriever
from lexrag.retrieval.filtering import matches_residual_filters, split_backend_filters
from lexrag.retrieval.metadata import materialize_hits
from lexrag.retrieval.schemas import DenseRetrieverConfig, RetrievalHit


class DenseRetriever(Retriever):
    """Query a dense vector store and apply retrieval-layer policies.

    The dense retriever stays intentionally small: it embeds the query, delegates
    approximate nearest-neighbor search to the indexing layer, and owns only the
    query-time concerns that should not leak into storage adapters.
    """

    def __init__(
        self,
        *,
        store: QdrantStore,
        embedder: BGEEmbedder,
        config: DenseRetrieverConfig | None = None,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.config = config or DenseRetrieverConfig()

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Return dense-retrieval results with query-time metadata attached."""

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
        """Return scored retrieval hits for downstream fusion or reranking."""

        normalized_query = self._normalize_query(query=query)
        if not normalized_query:
            return []
        limit = self._resolve_limit(top_k=top_k)
        backend_filters, residual_filters = split_backend_filters(metadata_filters)
        query_vector = self.embedder.embed_query(normalized_query)
        candidates = self.store.search_dense(
            query_vector,
            limit=max(limit, self.config.candidate_pool_size),
            metadata_filters=backend_filters,
        )
        return self._rank_candidates(
            candidates=candidates,
            query_vector=query_vector,
            limit=limit,
            residual_filters=residual_filters,
        )

    def _rank_candidates(
        self,
        *,
        candidates: list[Chunk],
        query_vector: list[float],
        limit: int,
        residual_filters: dict[str, dict[str, Any]],
    ) -> list[RetrievalHit]:
        """Score filtered dense candidates and emit stable hit records."""

        filtered = [
            chunk
            for chunk in candidates
            if matches_residual_filters(chunk, residual_filters)
        ]
        scored = self._sorted_scores(filtered=filtered, query_vector=query_vector)
        return self._build_hits(scored=scored[:limit])

    def _sorted_scores(
        self,
        *,
        filtered: list[Chunk],
        query_vector: list[float],
    ) -> list[tuple[Chunk, float]]:
        """Compute dense scores once and sort candidates by similarity."""

        scored = [
            (chunk, cosine_similarity(query_vector, chunk.embedding or []))
            for chunk in filtered
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored

    def _build_hits(self, *, scored: list[tuple[Chunk, float]]) -> list[RetrievalHit]:
        """Materialize dense scores into retrieval-hit records."""

        return [
            RetrievalHit(
                chunk=chunk,
                score=score,
                source="dense",
                rank=position,
                branch_scores={"dense_score": score},
            )
            for position, (chunk, score) in enumerate(scored, start=1)
        ]

    def _normalize_query(self, *, query: str) -> str:
        """Trim the incoming query to avoid empty retrieval calls."""

        return query.strip()

    def _resolve_limit(self, *, top_k: int | None) -> int:
        """Resolve and validate the requested result count."""

        if top_k is None:
            return self.config.top_k
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        return top_k
