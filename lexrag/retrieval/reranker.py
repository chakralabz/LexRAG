"""Deterministic retrieval reranker."""

from __future__ import annotations

from lexrag.indexing.schemas import Chunk
from lexrag.retrieval.metadata import materialize_hits
from lexrag.retrieval.reranker_base import Reranker
from lexrag.retrieval.schemas import RetrievalHit, TokenOverlapRerankerConfig
from lexrag.utils.text import TextNormalizer


class TokenOverlapReranker(Reranker):
    """Rerank candidates using normalized lexical overlap.

    This class is intentionally deterministic, fast, and dependency-free. It is
    appropriate for tests, offline evaluation, and as a production fallback when
    a model-based cross-encoder is unavailable.
    """

    def __init__(
        self,
        *,
        config: TokenOverlapRerankerConfig | None = None,
    ) -> None:
        self.config = config or TokenOverlapRerankerConfig()
        self.normalizer = TextNormalizer()

    def rerank(
        self,
        query: str,
        chunks: list[Chunk],
        *,
        top_k: int | None = None,
    ) -> list[Chunk]:
        """Return reranked chunks with reranker metadata attached."""

        hits = self.rerank_hits(query, chunks, top_k=top_k)
        return materialize_hits(hits, metadata_key="reranker")

    def rerank_hits(
        self,
        query: str,
        chunks: list[Chunk],
        *,
        top_k: int | None = None,
    ) -> list[RetrievalHit]:
        """Return scored reranker hits for downstream orchestration."""

        normalized_query = self.normalizer.token_set_words(query)
        if not normalized_query or not chunks:
            return []
        limit = self._resolve_limit(top_k=top_k)
        scored = self._score_chunks(query_terms=normalized_query, chunks=chunks)
        return [
            RetrievalHit(
                chunk=chunk,
                score=score,
                source="reranker",
                rank=position,
                branch_scores=self._branch_scores(
                    chunk=chunk,
                    score=score,
                    rank=position,
                ),
            )
            for position, (chunk, score) in enumerate(scored[:limit], start=1)
        ]

    def _score_chunks(
        self,
        *,
        query_terms: set[str],
        chunks: list[Chunk],
    ) -> list[tuple[Chunk, float]]:
        """Score chunks by overlap ratio and prior retrieval-rank tie-breaks."""

        scored = [
            (chunk, self._overlap_score(query_terms=query_terms, chunk=chunk))
            for chunk in chunks
        ]
        scored.sort(
            key=lambda item: (item[1], -self._retrieval_rank(chunk=item[0])),
            reverse=True,
        )
        return scored

    def _overlap_score(self, *, query_terms: set[str], chunk: Chunk) -> float:
        """Compute normalized lexical overlap between query and chunk text."""

        chunk_terms = self.normalizer.token_set_words(chunk.text)
        if not chunk_terms:
            return 0.0
        overlap = len(query_terms & chunk_terms)
        return overlap / len(query_terms)

    def _branch_scores(
        self,
        *,
        chunk: Chunk,
        score: float,
        rank: int,
    ) -> dict[str, float | bool]:
        """Build reranker metadata for one ranked chunk."""

        retrieval_rank = self._retrieval_rank(chunk=chunk)
        return {
            "reranker_score": score,
            "retrieval_rank": float(retrieval_rank),
            "reranker_rank": float(rank),
            "reranker_correction": rank < retrieval_rank,
        }

    def _retrieval_rank(self, *, chunk: Chunk) -> int:
        """Read the prior retrieval rank from chunk metadata when available."""

        retrieval_payload = chunk.metadata.metadata.get("retrieval", {})
        rank = retrieval_payload.get("rank")
        if isinstance(rank, int):
            return rank
        if isinstance(rank, float):
            return int(rank)
        return 10_000

    def _resolve_limit(self, *, top_k: int | None) -> int:
        """Resolve and validate the requested result count."""

        if top_k is None:
            return self.config.default_top_k
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        return top_k
