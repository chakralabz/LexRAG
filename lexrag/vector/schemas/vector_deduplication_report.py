"""Run-level report for vector-level deduplication."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.vector.schemas.vector_deduplication_decision import (
    VectorDeduplicationDecision,
)


class VectorDeduplicationReport(BaseModel):
    """Ordered audit trail for a vector deduplication pass.

    Attributes:
        decisions: One decision per candidate chunk, kept in evaluation order.
    """

    model_config = ConfigDict(frozen=True)

    decisions: list[VectorDeduplicationDecision] = Field(default_factory=list)
