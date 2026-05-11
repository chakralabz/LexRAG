from __future__ import annotations

from pathlib import Path

from lexrag.ingestion import IngestionDocumentResult, IngestionSummary
from lexrag.ingestion.jobs import IngestJobManager, IngestJobRepository


def test_ingest_job_manager_persists_completed_with_quarantine(tmp_path: Path) -> None:
    manager = IngestJobManager(repository=IngestJobRepository(root_dir=tmp_path))
    running = manager.start(
        job_id="job_1",
        request_id="req_1",
        paths=["/tmp/a.pdf"],
    )
    summary = IngestionSummary(
        documents_seen=1,
        chunks_created=0,
        chunks_after_dedup=0,
        chunks_indexed=0,
        quarantined_documents=1,
        parse_failure_counts={"manual_recovery_required": 1},
        document_results=[
            IngestionDocumentResult(
                path="/tmp/a.pdf",
                status="quarantined",
                chunks_created=0,
                parse_failure_reason="manual_recovery_required",
            )
        ],
    )

    completed = manager.complete(record=running, summary=summary)
    stored = manager.get(job_id="job_1")

    assert completed.status == "completed_with_quarantine"
    assert stored == completed


def test_ingest_job_manager_tracks_idempotency_and_replay_attempts(
    tmp_path: Path,
) -> None:
    manager = IngestJobManager(repository=IngestJobRepository(root_dir=tmp_path))

    original = manager.start(
        job_id="job_1",
        request_id="req_1",
        paths=["/tmp/a.pdf"],
        idempotency_key="same-request",
    )
    replay = manager.start(
        job_id="job_2",
        request_id="req_2",
        paths=["/tmp/a.pdf"],
        replay_of_job_id="job_1",
        replay_mode="failed_or_quarantined",
    )

    found = manager.idempotent_job(idempotency_key="same-request")

    assert found == original
    assert replay.attempt_number == 2
