"""Lifecycle manager for persisted ingest jobs."""

from __future__ import annotations

from datetime import UTC, datetime

from lexrag.ingestion.ingestion_summary import IngestionSummary
from lexrag.ingestion.jobs.ingest_job_record import IngestJobRecord
from lexrag.ingestion.jobs.ingest_job_repository import IngestJobRepository


class IngestJobManager:
    """Create and update ingest job records around pipeline execution."""

    def __init__(self, *, repository: IngestJobRepository) -> None:
        self.repository = repository

    def start(
        self,
        *,
        job_id: str,
        request_id: str,
        paths: list[str],
        idempotency_key: str | None = None,
        replay_of_job_id: str | None = None,
        replay_mode: str | None = None,
    ) -> IngestJobRecord:
        """Persist a newly started ingest job."""
        now = self._now()
        return self.repository.save(
            record=IngestJobRecord(
                job_id=job_id,
                request_id=request_id,
                status="running",
                paths=paths,
                attempt_number=self.repository.next_attempt_number(
                    replay_of_job_id=replay_of_job_id
                ),
                idempotency_key=idempotency_key,
                replay_of_job_id=replay_of_job_id,
                replay_mode=replay_mode,
                created_at=now,
                updated_at=now,
            )
        )

    def idempotent_job(self, *, idempotency_key: str) -> IngestJobRecord | None:
        """Return the latest job recorded for one idempotency key."""
        return self.repository.find_by_idempotency_key(idempotency_key=idempotency_key)

    def complete(
        self,
        *,
        record: IngestJobRecord,
        summary: IngestionSummary,
    ) -> IngestJobRecord:
        """Persist successful job completion."""
        return self.repository.save(
            record=record.model_copy(
                update={
                    "status": self._completed_status(summary=summary),
                    "summary": summary,
                    "updated_at": self._now(),
                }
            )
        )

    def fail(self, *, record: IngestJobRecord, error_message: str) -> IngestJobRecord:
        """Persist job failure details."""
        return self.repository.save(
            record=record.model_copy(
                update={
                    "status": "failed",
                    "error_message": error_message,
                    "updated_at": self._now(),
                }
            )
        )

    def get(self, *, job_id: str) -> IngestJobRecord | None:
        """Load one persisted job record."""
        return self.repository.get(job_id=job_id)

    def _completed_status(self, *, summary: IngestionSummary) -> str:
        if summary.quarantined_documents > 0:
            return "completed_with_quarantine"
        return "completed"

    def _now(self) -> datetime:
        return datetime.now(UTC)
