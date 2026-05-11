"""Configuration schema for sparse retrieval."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SparseRetrieverConfig(BaseModel):
    """Define sparse retrieval behavior and candidate-pool sizing.

    Attributes:
        top_k: Default number of chunks returned to callers.
        candidate_pool_size: Backend fetch size before residual filtering trims
            the result set.
    """

    model_config = ConfigDict(frozen=True)

    top_k: int = Field(default=10, ge=1, le=100)
    candidate_pool_size: int = Field(default=40, ge=1, le=500)
