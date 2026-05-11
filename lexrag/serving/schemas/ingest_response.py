"""HTTP response contract for ingestion work."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.ingestion.ingestion_summary import IngestionSummary
from lexrag.ingestion.jobs.ingest_job_record import IngestJobRecord


class IngestResponse(BaseModel):
    """Return a stable ingestion summary to API callers."""

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1)
    job: IngestJobRecord
    summary: IngestionSummary | None = None
