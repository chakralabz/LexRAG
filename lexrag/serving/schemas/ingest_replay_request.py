"""HTTP request contract for replaying a prior ingest job."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IngestReplayRequest(BaseModel):
    """Capture replay mode and optional idempotency for job reprocessing."""

    model_config = ConfigDict(frozen=True)

    mode: Literal["failed_or_quarantined", "all"] = "failed_or_quarantined"
    idempotency_key: str | None = Field(default=None, min_length=1)
