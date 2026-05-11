"""Structured decision model for one deduplication outcome."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BlockDeduplicationDecision(BaseModel):
    """Audit record describing how one block was handled.

    Attributes:
        block_id: Identifier of the candidate block.
        dedup_status: Whether the block was kept or dropped.
        dedup_method: Technique that triggered the decision, when applicable.
        near_duplicate_of: Identifier of the earlier retained block that caused
            suppression.
        dedup_confidence: Similarity/confidence score for the decision.
        dedup_bypass_reason: Stable policy label when a duplicate was preserved.
    """

    model_config = ConfigDict(frozen=True)

    block_id: str = Field(description="Deterministic ID of the evaluated block.")
    dedup_status: str = Field(description="`kept` or `dropped`.")
    dedup_method: str | None = Field(
        default=None,
        description="Deduplication technique that drove the decision.",
    )
    near_duplicate_of: str | None = Field(
        default=None,
        description="Earlier retained block that matched this candidate.",
    )
    dedup_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence or similarity score for the decision.",
    )
    dedup_bypass_reason: str | None = Field(
        default=None,
        description="Stable bypass reason when policy preserved the block.",
    )
