"""Ranked retrieval result contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.indexing.schemas import Chunk


class RetrievalHit(BaseModel):
    """Capture one scored retrieval candidate before response materialization.

    Attributes:
        chunk: Canonical chunk payload returned by storage.
        score: Branch-specific score used for ranking or fusion.
        source: Stable retrieval source label such as ``dense``, ``sparse``, or
            ``hybrid``.
        rank: One-based rank within the producing strategy.
        branch_scores: Additional scores keyed by strategy name. This keeps
            rank-fusion and reranking metadata explicit without mutating the
            canonical chunk schema itself.
    """

    model_config = ConfigDict(frozen=True)

    chunk: Chunk
    score: float = Field(default=0.0)
    source: str = Field(min_length=1)
    rank: int = Field(ge=1)
    branch_scores: dict[str, float | bool] = Field(default_factory=dict)
