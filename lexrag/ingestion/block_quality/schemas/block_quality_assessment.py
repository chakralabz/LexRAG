"""Assessment schema for one validated block."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BlockQualityAssessment(BaseModel):
    """Audit record describing a block-quality decision."""

    model_config = ConfigDict(frozen=True)

    block_id: str = Field(description="Identifier of the validated block.")
    quality_status: str = Field(description="`passed`, `flagged`, or `dropped`.")
    quality_flags: list[str] = Field(default_factory=list)
    drop_reason: str | None = Field(default=None)
