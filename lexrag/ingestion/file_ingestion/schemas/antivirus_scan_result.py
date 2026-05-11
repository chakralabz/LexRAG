"""Schema for antivirus scan results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AntivirusScanResult(BaseModel):
    """Normalized malware scan output independent of the underlying vendor."""

    model_config = ConfigDict(frozen=True)

    engine_name: str = Field(
        description="Scanner implementation that produced the result."
    )
    status: Literal["clean", "infected", "skipped", "error"] = Field(
        description="Normalized scanner outcome."
    )
    details: str | None = Field(
        default=None,
        description="Human-readable detail that can be surfaced in logs or UI.",
    )
    signature_name: str | None = Field(
        default=None,
        description="Detected malware signature when the file is infected.",
    )
    blocking: bool = Field(
        description="Whether the result should block the file from entering parsing."
    )
