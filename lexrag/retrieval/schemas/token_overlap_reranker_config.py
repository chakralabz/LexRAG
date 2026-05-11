"""Configuration schema for the deterministic token-overlap reranker."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TokenOverlapRerankerConfig(BaseModel):
    """Tune the lexical reranker used in tests and offline evaluation.

    Attributes:
        default_top_k: Default number of reranked chunks to return.
    """

    model_config = ConfigDict(frozen=True)

    default_top_k: int = Field(default=5, ge=1, le=100)
