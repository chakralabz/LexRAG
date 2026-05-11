"""Run-level report for the deduplication layer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.ingestion.deduplicator.schemas.block_deduplication_decision import (
    BlockDeduplicationDecision,
)


class DeduplicationRunReport(BaseModel):
    """Ordered audit report for one deduplication pass."""

    model_config = ConfigDict(frozen=True)

    decisions: list[BlockDeduplicationDecision] = Field(default_factory=list)
