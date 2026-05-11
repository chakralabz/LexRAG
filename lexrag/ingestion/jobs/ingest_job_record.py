"""Persisted ingest job record."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from lexrag.ingestion.ingestion_summary import IngestionSummary


class IngestJobRecord(BaseModel):
    """Represents one persisted ingestion job and its current state."""

    model_config = ConfigDict(frozen=True)

    job_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    paths: list[str] = Field(min_length=1)
    attempt_number: int = Field(default=1, ge=1)
    idempotency_key: str | None = None
    replay_of_job_id: str | None = None
    replay_mode: str | None = None
    created_at: datetime
    updated_at: datetime
    summary: IngestionSummary | None = None
    error_message: str | None = None
