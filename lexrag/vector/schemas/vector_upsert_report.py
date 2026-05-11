"""Structured result for one vector store upsert operation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.vector.schemas.reindex_plan import ReindexPlan


class VectorUpsertReport(BaseModel):
    """Summarizes one version-aware vector write.

    Attributes:
        attempted_chunks: Number of chunks received by the store.
        indexed_chunks: Number of chunks written to the backend.
        suppressed_chunks: Number of chunks removed by vector deduplication.
        replaced_chunks: Number of stale chunks removed after a successful
            version replacement.
        rollback_performed: Whether stale chunks had to be restored.
        document_ids: Distinct document IDs affected by the write.
        reindex_plans: Document-level plans executed for this write.
    """

    model_config = ConfigDict(frozen=True)

    attempted_chunks: int = Field(ge=0)
    indexed_chunks: int = Field(ge=0)
    suppressed_chunks: int = Field(ge=0)
    replaced_chunks: int = Field(ge=0)
    rollback_performed: bool = Field(default=False)
    document_ids: list[str] = Field(default_factory=list)
    reindex_plans: list[ReindexPlan] = Field(default_factory=list)
