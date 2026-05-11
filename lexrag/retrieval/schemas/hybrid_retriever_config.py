"""Configuration schema for hybrid retrieval fusion."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class HybridRetrieverConfig(BaseModel):
    """Tune hybrid retrieval fusion behavior.

    Attributes:
        top_k: Default number of returned chunks.
        prefetch_k: Number of candidates requested from each retriever before
            reciprocal-rank fusion.
        rrf_k: Dampening constant used by reciprocal-rank fusion.
        dense_weight: Relative contribution of the dense branch.
        sparse_weight: Relative contribution of the sparse branch.
    """

    model_config = ConfigDict(frozen=True)

    top_k: int = Field(default=10, ge=1, le=100)
    prefetch_k: int = Field(default=40, ge=1, le=500)
    rrf_k: int = Field(default=60, ge=1, le=1000)
    dense_weight: float = Field(default=1.0, ge=0.0, le=10.0)
    sparse_weight: float = Field(default=1.0, ge=0.0, le=10.0)

    @model_validator(mode="after")
    def validate_weights(self) -> HybridRetrieverConfig:
        """Reject a configuration that disables both retrieval branches."""
        if self.dense_weight == 0.0 and self.sparse_weight == 0.0:
            raise ValueError("At least one hybrid retrieval weight must be positive")
        if self.prefetch_k < self.top_k:
            raise ValueError("prefetch_k must be greater than or equal to top_k")
        return self
