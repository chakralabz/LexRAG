"""HTTP response model for ingest job lookup."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from lexrag.ingestion.jobs.ingest_job_record import IngestJobRecord


class IngestJobResponse(BaseModel):
    """Return one persisted ingest job record to API callers."""

    model_config = ConfigDict(frozen=True)

    job: IngestJobRecord
