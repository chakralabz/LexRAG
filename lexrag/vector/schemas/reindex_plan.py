"""Schema describing one document-level re-index plan."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReindexPlan(BaseModel):
    """Captures how one document lineage will be rewritten.

    Attributes:
        document_id: Document lineage identifier.
        incoming_version: Version carried by the incoming batch, if any.
        incoming_chunk_ids: Deterministic chunk IDs scheduled for write.
        stale_chunk_ids: Existing chunk IDs that should be removed after a
            successful replacement write.
        replacement_required: Whether the batch replaces an older version.
    """

    model_config = ConfigDict(frozen=True)

    document_id: str = Field(description="Document lineage identifier.")
    incoming_version: str | None = Field(default=None)
    incoming_chunk_ids: list[str] = Field(default_factory=list)
    stale_chunk_ids: list[str] = Field(default_factory=list)
    replacement_required: bool = Field(default=False)
