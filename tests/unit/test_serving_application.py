from __future__ import annotations

from pathlib import Path

from lexrag.context_builder import LLMContextBuilder
from lexrag.generation import AnswerGenerator
from lexrag.generation.llm_backend import LLMBackend
from lexrag.indexing.schemas import Chunk, ChunkMetadata
from lexrag.ingestion import IngestionDocumentResult, IngestionSummary
from lexrag.ingestion.jobs import IngestJobManager, IngestJobRepository
from lexrag.serving.lexrag_application import LexRAGApplication
from lexrag.serving.runtime_dependencies import RuntimeDependencies
from lexrag.serving.schemas import IngestReplayRequest, IngestRequest, QueryRequest


class FakeBackend(LLMBackend):
    def __init__(self, *, response: str) -> None:
        self.response = response

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        return self.response


class FakePipeline:
    def __init__(self, *, summary: IngestionSummary | None = None) -> None:
        self.summary = summary
        self.seen_paths: list[list[str]] = []

    def ingest_documents(self, paths: list) -> IngestionSummary:
        self.seen_paths.append([str(path) for path in paths])
        if self.summary is None:
            raise AssertionError("ingest should not run in this test")
        return self.summary


class FakeRetriever:
    def __init__(self, *, chunks: list[Chunk]) -> None:
        self.chunks = chunks

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        metadata_filters: dict | None = None,
    ) -> list[Chunk]:
        _ = query, top_k, metadata_filters
        return list(self.chunks)


def _application(
    *,
    generator: AnswerGenerator | None,
    jobs_root: Path,
    ingest_root: Path,
    pipeline: FakePipeline | None = None,
    http_ingest_enabled: bool = False,
) -> LexRAGApplication:
    manager = IngestJobManager(repository=IngestJobRepository(root_dir=jobs_root))
    dependencies = RuntimeDependencies(
        ingestion_pipeline=pipeline or FakePipeline(),  # type: ignore[arg-type]
        ingest_job_manager=manager,
        retriever=FakeRetriever(chunks=[_chunk()]),  # type: ignore[arg-type]
        context_builder=LLMContextBuilder(),
        generator=generator,
    )
    return LexRAGApplication(
        dependencies=dependencies,
        ingest_root=ingest_root,
        http_ingest_enabled=http_ingest_enabled,
    )


def _chunk() -> Chunk:
    metadata = ChunkMetadata(
        doc_id="doc_1",
        source_path="/tmp/msa-v3.pdf",
        chunk_index=0,
        total_chunks=1,
        page_start=1,
        page_end=1,
        section_title="Liability",
        source_block_ids=["block_1"],
    )
    return Chunk(
        chunk_id="doc_1_chunk_1",
        text="The liability cap is $100,000.",
        metadata=metadata,
    )


def test_application_reports_not_ready_without_generator(tmp_path: Path) -> None:
    application = _application(
        generator=None,
        jobs_root=tmp_path / "jobs",
        ingest_root=tmp_path / "ingest",
    )

    readiness = application.readiness()

    assert readiness.ready is False
    assert readiness.issues == ["generator_unconfigured"]


def test_application_query_returns_generated_answer(tmp_path: Path) -> None:
    application = _application(
        generator=AnswerGenerator(
            backend=FakeBackend(response="The liability cap is $100,000 [1].")
        ),
        jobs_root=tmp_path / "jobs",
        ingest_root=tmp_path / "ingest",
    )

    response = application.query(
        QueryRequest(question="What is the liability cap?"),
        request_id="req_123",
    )

    assert response.request_id == "req_123"
    assert response.answer_text == "The liability cap is $100,000 [1]."
    assert response.validation.is_valid is True
    assert response.retrieved_chunk_ids == ["doc_1_chunk_1"]


def test_application_ingest_persists_completed_job(tmp_path: Path) -> None:
    ingest_root = _ingest_root(tmp_path)
    summary = IngestionSummary(
        documents_seen=1,
        chunks_created=2,
        chunks_after_dedup=2,
        chunks_indexed=2,
        document_results=[
            IngestionDocumentResult(
                path="/tmp/a.pdf",
                status="completed",
                chunks_created=2,
            )
        ],
    )
    application = _application(
        generator=None,
        jobs_root=tmp_path / "jobs",
        ingest_root=ingest_root,
        pipeline=FakePipeline(summary=summary),
        http_ingest_enabled=True,
    )

    response = application.ingest(
        IngestRequest(documents=["a.pdf"]),
        request_id="req_ingest",
    )
    stored = application.ingest_job(job_id=response.job.job_id)

    assert response.request_id == "req_ingest"
    assert response.job.status == "completed"
    assert stored.job.summary == summary
    assert stored.job.paths == [str(ingest_root / "a.pdf")]


def test_application_reuses_completed_idempotent_ingest(tmp_path: Path) -> None:
    ingest_root = _ingest_root(tmp_path)
    summary = IngestionSummary(
        documents_seen=1,
        chunks_created=1,
        chunks_after_dedup=1,
        chunks_indexed=1,
    )
    pipeline = FakePipeline(summary=summary)
    application = _application(
        generator=None,
        jobs_root=tmp_path / "jobs",
        ingest_root=ingest_root,
        pipeline=pipeline,
        http_ingest_enabled=True,
    )

    first = application.ingest(
        IngestRequest(documents=["a.pdf"], idempotency_key="same"),
        request_id="req_1",
    )
    second = application.ingest(
        IngestRequest(documents=["a.pdf"], idempotency_key="same"),
        request_id="req_2",
    )

    assert first.job.job_id == second.job.job_id
    assert len(pipeline.seen_paths) == 1


def test_application_replays_only_quarantined_documents(tmp_path: Path) -> None:
    ingest_root = _ingest_root(tmp_path, names=["good.pdf", "bad.pdf"])
    initial_summary = IngestionSummary(
        documents_seen=2,
        chunks_created=1,
        chunks_after_dedup=1,
        chunks_indexed=1,
        quarantined_documents=1,
        document_results=[
            IngestionDocumentResult(
                path="/tmp/good.pdf",
                status="completed",
                chunks_created=1,
            ),
            IngestionDocumentResult(
                path="/tmp/bad.pdf",
                status="quarantined",
                chunks_created=0,
                parse_failure_reason="manual_recovery_required",
            ),
        ],
    )
    replay_summary = IngestionSummary(
        documents_seen=1,
        chunks_created=1,
        chunks_after_dedup=1,
        chunks_indexed=1,
        document_results=[
            IngestionDocumentResult(
                path="/tmp/bad.pdf",
                status="completed",
                chunks_created=1,
            )
        ],
    )
    pipeline = FakePipeline(summary=initial_summary)
    application = _application(
        generator=None,
        jobs_root=tmp_path / "jobs",
        ingest_root=ingest_root,
        pipeline=pipeline,
        http_ingest_enabled=True,
    )
    original = application.ingest(
        IngestRequest(documents=["good.pdf", "bad.pdf"]),
        request_id="req_1",
    )
    pipeline.summary = replay_summary

    replayed = application.replay_ingest_job(
        job_id=original.job.job_id,
        request=IngestReplayRequest(mode="failed_or_quarantined"),
        request_id="req_2",
    )

    assert replayed.job.replay_of_job_id == original.job.job_id
    assert replayed.job.attempt_number == 2
    assert pipeline.seen_paths[-1] == ["/tmp/bad.pdf"]


def test_application_ingest_requires_explicit_http_enablement(tmp_path: Path) -> None:
    ingest_root = _ingest_root(tmp_path)
    summary = IngestionSummary(
        documents_seen=1,
        chunks_created=1,
        chunks_after_dedup=1,
        chunks_indexed=1,
    )
    application = _application(
        generator=None,
        jobs_root=tmp_path / "jobs",
        ingest_root=ingest_root,
        pipeline=FakePipeline(summary=summary),
    )

    try:
        application.ingest(IngestRequest(documents=["a.pdf"]), request_id="req_ingest")
    except PermissionError as exc:
        assert str(exc) == "http_ingest_disabled"
    else:
        raise AssertionError("Expected ingest to be disabled by default")


def _ingest_root(tmp_path: Path, names: list[str] | None = None) -> Path:
    names = names or ["a.pdf"]
    ingest_root = tmp_path / "ingest"
    ingest_root.mkdir()
    for name in names:
        (ingest_root / name).write_text("sample", encoding="utf-8")
    return ingest_root
