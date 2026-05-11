"""Rank-fusion helpers for hybrid retrieval."""

from __future__ import annotations

from collections import defaultdict
from functools import partial

from lexrag.retrieval.schemas import RetrievalHit


def reciprocal_rank_fuse(
    *,
    dense_hits: list[RetrievalHit],
    sparse_hits: list[RetrievalHit],
    rrf_k: int,
    dense_weight: float,
    sparse_weight: float,
) -> list[RetrievalHit]:
    """Fuse dense and sparse rankings using reciprocal-rank fusion."""

    fused_scores: defaultdict[str, float] = defaultdict(float)
    payloads: dict[str, RetrievalHit] = {}
    dense_ranks = {hit.chunk.chunk_id: hit.rank for hit in dense_hits}
    sparse_ranks = {hit.chunk.chunk_id: hit.rank for hit in sparse_hits}
    _accumulate_scores(
        hits=dense_hits,
        weight=dense_weight,
        rrf_k=rrf_k,
        fused_scores=fused_scores,
        payloads=payloads,
    )
    _accumulate_scores(
        hits=sparse_hits,
        weight=sparse_weight,
        rrf_k=rrf_k,
        fused_scores=fused_scores,
        payloads=payloads,
    )
    return _build_fused_hits(
        fused_scores=fused_scores,
        payloads=payloads,
        dense_ranks=dense_ranks,
        sparse_ranks=sparse_ranks,
    )


def _accumulate_scores(
    *,
    hits: list[RetrievalHit],
    weight: float,
    rrf_k: int,
    fused_scores: defaultdict[str, float],
    payloads: dict[str, RetrievalHit],
) -> None:
    """Add weighted reciprocal-rank contributions for one retrieval branch."""

    for hit in hits:
        chunk_id = hit.chunk.chunk_id
        fused_scores[chunk_id] += weight / (rrf_k + hit.rank)
        payloads.setdefault(chunk_id, hit)


def _build_fused_hits(
    *,
    fused_scores: defaultdict[str, float],
    payloads: dict[str, RetrievalHit],
    dense_ranks: dict[str, int],
    sparse_ranks: dict[str, int],
) -> list[RetrievalHit]:
    """Materialize fused scores into ranked retrieval hits."""

    sorted_ids = sorted(
        fused_scores,
        key=partial(_fused_score, fused_scores=fused_scores),
        reverse=True,
    )
    fused_hits: list[RetrievalHit] = []
    for position, chunk_id in enumerate(sorted_ids, start=1):
        base_hit = payloads[chunk_id]
        fused_hits.append(
            RetrievalHit(
                chunk=base_hit.chunk,
                score=fused_scores[chunk_id],
                source="hybrid",
                rank=position,
                branch_scores=_branch_scores(
                    chunk_id=chunk_id,
                    score=fused_scores[chunk_id],
                    dense_ranks=dense_ranks,
                    sparse_ranks=sparse_ranks,
                ),
            )
        )
    return fused_hits


def _branch_scores(
    *,
    chunk_id: str,
    score: float,
    dense_ranks: dict[str, int],
    sparse_ranks: dict[str, int],
) -> dict[str, float]:
    """Return retrieval-branch metadata for one fused hit."""

    payload: dict[str, float] = {"hybrid_score": score}
    dense_rank = dense_ranks.get(chunk_id)
    sparse_rank = sparse_ranks.get(chunk_id)
    if dense_rank is not None:
        payload["dense_rank"] = float(dense_rank)
    if sparse_rank is not None:
        payload["sparse_rank"] = float(sparse_rank)
    return payload


def _fused_score(chunk_id: str, *, fused_scores: defaultdict[str, float]) -> float:
    """Return the stored fused score for one chunk identifier."""

    return fused_scores[chunk_id]
