"""Chunk-materialization helpers for retrieval and reranking metadata."""

from __future__ import annotations

from typing import Any

from lexrag.indexing.schemas import Chunk
from lexrag.retrieval.schemas import RetrievalHit


def materialize_hits(hits: list[RetrievalHit], *, metadata_key: str) -> list[Chunk]:
    """Return chunks with retrieval metadata copied into chunk metadata.

    Args:
        hits: Ranked retrieval or reranking hits.
        metadata_key: Key written inside ``chunk.metadata.metadata``. This keeps
            query-time annotations namespaced and avoids polluting the canonical
            chunk schema with transient serving concerns.

    Returns:
        Chunks with immutable metadata copied and enriched for downstream
        inspection.
    """

    return [_materialize_one_hit(hit=hit, metadata_key=metadata_key) for hit in hits]


def _materialize_one_hit(*, hit: RetrievalHit, metadata_key: str) -> Chunk:
    """Attach one retrieval-hit payload to an immutable chunk copy."""

    metadata_payload = dict(hit.chunk.metadata.metadata)
    metadata_payload[metadata_key] = _hit_metadata(hit=hit)
    metadata = hit.chunk.metadata.model_copy(update={"metadata": metadata_payload})
    return hit.chunk.model_copy(update={"metadata": metadata})


def _hit_metadata(*, hit: RetrievalHit) -> dict[str, Any]:
    """Build a compact metadata record for one hit."""

    payload: dict[str, Any] = {
        "source": hit.source,
        "score": hit.score,
        "rank": hit.rank,
    }
    payload.update(hit.branch_scores)
    return payload
