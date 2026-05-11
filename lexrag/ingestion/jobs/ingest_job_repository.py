"""Filesystem-backed repository for persisted ingest jobs."""

from __future__ import annotations

import json
from pathlib import Path

from lexrag.ingestion.jobs.ingest_job_record import IngestJobRecord


class IngestJobRepository:
    """Store one JSON file per ingest job for operator lookup and replay."""

    def __init__(self, *, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save(self, *, record: IngestJobRecord) -> IngestJobRecord:
        """Persist a job record atomically."""
        path = self._path(job_id=record.job_id)
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temp_path.replace(path)
        return record

    def get(self, *, job_id: str) -> IngestJobRecord | None:
        """Load one persisted job record by ID."""
        path = self._path(job_id=job_id)
        if not path.exists():
            return None
        return IngestJobRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def list_records(self) -> list[IngestJobRecord]:
        """Return all persisted ingest job records."""
        return [
            self._read_record(path=path)
            for path in sorted(self.root_dir.glob("*.json"))
        ]

    def find_by_idempotency_key(
        self, *, idempotency_key: str
    ) -> IngestJobRecord | None:
        """Return the latest job recorded for one idempotency key."""
        matches = [
            record
            for record in self.list_records()
            if record.idempotency_key == idempotency_key
        ]
        if not matches:
            return None
        matches.sort(key=lambda record: record.updated_at, reverse=True)
        return matches[0]

    def next_attempt_number(self, *, replay_of_job_id: str | None) -> int:
        """Return the next attempt number for a root or replayed job lineage."""
        if replay_of_job_id is None:
            return 1
        related = [
            record.attempt_number
            for record in self.list_records()
            if record.job_id == replay_of_job_id
            or record.replay_of_job_id == replay_of_job_id
        ]
        return (max(related) if related else 1) + 1

    def _path(self, *, job_id: str) -> Path:
        return self.root_dir / f"{job_id}.json"

    def _read_record(self, *, path: Path) -> IngestJobRecord:
        return IngestJobRecord.model_validate_json(path.read_text(encoding="utf-8"))
