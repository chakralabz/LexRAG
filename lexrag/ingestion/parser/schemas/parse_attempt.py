"""Schema for parser backend execution attempts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ParseAttempt(BaseModel):
    """Captures one parser backend attempt in the fallback chain."""

    model_config = ConfigDict(frozen=True)

    parser_name: str = Field(description="Stable backend name.")
    succeeded: bool = Field(description="Whether this attempt succeeded.")
    fallback_step: int = Field(
        ge=1, description="One-based position in the parser chain."
    )
    produced_blocks: int = Field(
        ge=0, description="Number of blocks emitted on success."
    )
    failure_reason: str | None = Field(
        default=None,
        description="Stable failure reason code when the attempt fails.",
    )
    error_type: str | None = Field(
        default=None,
        description="Exception type captured for observability.",
    )
    error_message: str | None = Field(
        default=None,
        description="Exception message captured for observability.",
    )
