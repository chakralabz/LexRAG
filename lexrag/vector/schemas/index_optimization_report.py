"""Structured result emitted by the index optimization layer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class IndexOptimizationReport(BaseModel):
    """Describes what index optimization configured for a backend.

    Attributes:
        backend_name: Backend that was optimized.
        dense_algorithm: Dense optimization strategy that was applied.
        sparse_strategy: Sparse optimization strategy that was applied.
        metadata_indexes: Metadata fields ensured on the backend.
    """

    model_config = ConfigDict(frozen=True)

    backend_name: str = Field(description="Optimized backend identifier.")
    dense_algorithm: str | None = Field(default=None)
    sparse_strategy: str | None = Field(default=None)
    metadata_indexes: list[str] = Field(default_factory=list)
