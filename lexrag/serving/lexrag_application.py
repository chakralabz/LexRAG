"""Serving composition root for the LexRAG HTTP surface."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from lexrag.citation import CitationDocument
from lexrag.context_builder.schemas import ContextWindow
from lexrag.generation import AnswerGenerator
from lexrag.generation.schemas import GenerationRequest, GenerationResponse
from lexrag.indexing.schemas import Chunk
from lexrag.observability.request_context import request_context
from lexrag.serving.runtime_dependencies import RuntimeDependencies
from lexrag.serving.schemas import (
    HealthResponse,
    IngestJobResponse,
    IngestReplayRequest,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    ServiceReadiness,
)
from lexrag.serving.service_unavailable_error import ServiceUnavailableError


class LexRAGApplication:
    """Own the serving-layer orchestration and readiness policy."""

    def __init__(
        self,
        *,
        dependencies: RuntimeDependencies,
        ingest_root: Path,
        http_ingest_enabled: bool = False,
    ) -> None:
        self.dependencies = dependencies
        self.ingest_root = ingest_root.expanduser().resolve()
        self.http_ingest_enabled = http_ingest_enabled

    def health(self) -> HealthResponse:
        """Return liveness plus readiness state for operators."""
        return HealthResponse(
            status="ok",
            service="lexrag",
            readiness=self.readiness(),
        )

    def readiness(self) -> ServiceReadiness:
        """Evaluate whether the query surface can safely accept traffic."""
        issues = self._readiness_issues()
        return ServiceReadiness(ready=not issues, issues=issues)

    def ingest(
        self,
        request: IngestRequest,
        *,
        request_id: str | None = None,
    ) -> IngestResponse:
        """Ingest documents through the canonical pipeline."""
        self._ensure_http_ingest_enabled()
        resolved_request_id = request_id or self._request_id()
        existing = self._idempotent_job(idempotency_key=request.idempotency_key)
        if existing is not None:
            return self._ingest_response(request_id=resolved_request_id, job=existing)
        resolved_paths = self._paths(request=request)
        job = self.dependencies.ingest_job_manager.start(
            job_id=self._job_id(),
            request_id=resolved_request_id,
            paths=[str(path) for path in resolved_paths],
            idempotency_key=request.idempotency_key,
        )
        with request_context(resolved_request_id):
            try:
                summary = self.dependencies.ingestion_pipeline.ingest_documents(
                    resolved_paths
                )
            except Exception as exc:
                self.dependencies.ingest_job_manager.fail(
                    record=job,
                    error_message=str(exc),
                )
                raise
        completed = self.dependencies.ingest_job_manager.complete(
            record=job,
            summary=summary,
        )
        return self._ingest_response(request_id=resolved_request_id, job=completed)

    def ingest_job(self, *, job_id: str) -> IngestJobResponse:
        """Return one persisted ingest job record for operator lookup."""
        job = self.dependencies.ingest_job_manager.get(job_id=job_id)
        if job is None:
            raise ValueError(f"Unknown ingest job: {job_id}")
        return IngestJobResponse(job=job)

    def replay_ingest_job(
        self,
        *,
        job_id: str,
        request: IngestReplayRequest,
        request_id: str | None = None,
    ) -> IngestResponse:
        """Replay a prior ingest job using selected document outcomes."""
        self._ensure_http_ingest_enabled()
        source = self._require_job(job_id=job_id)
        resolved_request_id = request_id or self._request_id()
        existing = self._idempotent_job(idempotency_key=request.idempotency_key)
        if existing is not None:
            return self._ingest_response(request_id=resolved_request_id, job=existing)
        replay_paths = self._replay_paths(source=source, mode=request.mode)
        if not replay_paths:
            raise ValueError(f"No replayable documents found for job: {job_id}")
        job = self.dependencies.ingest_job_manager.start(
            job_id=self._job_id(),
            request_id=resolved_request_id,
            paths=replay_paths,
            idempotency_key=request.idempotency_key,
            replay_of_job_id=source.job_id,
            replay_mode=request.mode,
        )
        with request_context(resolved_request_id):
            try:
                summary = self.dependencies.ingestion_pipeline.ingest_documents(
                    [Path(path) for path in replay_paths]
                )
            except Exception as exc:
                self.dependencies.ingest_job_manager.fail(
                    record=job,
                    error_message=str(exc),
                )
                raise
        completed = self.dependencies.ingest_job_manager.complete(
            record=job,
            summary=summary,
        )
        return self._ingest_response(request_id=resolved_request_id, job=completed)

    def query(
        self,
        request: QueryRequest,
        *,
        request_id: str | None = None,
    ) -> QueryResponse:
        """Run retrieval, context building, and generation for one query."""
        resolved_request_id = request_id or self._request_id()
        self._ensure_query_ready()
        with request_context(resolved_request_id):
            chunks = self._retrieve(request=request)
            context_window, generation = self._generate(request=request, chunks=chunks)
        return QueryResponse(
            request_id=resolved_request_id,
            answer_text=generation.answer_text,
            validation=generation.validation,
            retrieved_chunk_ids=[chunk.chunk_id for chunk in chunks],
            context_warnings=context_window.warnings,
        )

    def _ensure_query_ready(self) -> None:
        issues = self._readiness_issues()
        if not issues:
            return
        raise ServiceUnavailableError(
            "LexRAG query service is not ready",
            details={"issues": issues},
        )

    def _retrieve(self, *, request: QueryRequest) -> list[Chunk]:
        return self.dependencies.retriever.retrieve(
            request.question,
            top_k=request.top_k,
            metadata_filters=request.metadata_filters,
        )

    def _generate(
        self,
        *,
        request: QueryRequest,
        chunks: list[Chunk],
    ) -> tuple[ContextWindow, GenerationResponse]:
        context_window = self.dependencies.context_builder.build(
            query=request.question,
            chunks=chunks,
            document_catalog=self._document_catalog(chunks=chunks),
        )
        generation_request = GenerationRequest(
            question=request.question,
            context_window=context_window,
        )
        return context_window, self._generator().generate(generation_request)

    def _document_catalog(self, *, chunks: list[Chunk]) -> dict[str, CitationDocument]:
        catalog: dict[str, CitationDocument] = {}
        for chunk in chunks:
            document_id = chunk.metadata.doc_id
            if not document_id or document_id in catalog:
                continue
            catalog[document_id] = CitationDocument(
                document_id=document_id,
                title=self._title(chunk=chunk),
                version=chunk.metadata.document_version,
            )
        return catalog

    def _title(self, *, chunk: Chunk) -> str:
        source_path = chunk.metadata.source_path or chunk.metadata.doc_id or "document"
        return Path(source_path).name

    def _paths(self, *, request: IngestRequest) -> list[Path]:
        return [self._resolve_document(document=document) for document in request.documents]

    def _readiness_issues(self) -> list[str]:
        issues: list[str] = []
        if self.dependencies.generator is None:
            issues.append("generator_unconfigured")
        return issues

    def _ensure_http_ingest_enabled(self) -> None:
        if self.http_ingest_enabled:
            return
        raise PermissionError("http_ingest_disabled")

    def _generator(self) -> AnswerGenerator:
        generator = self.dependencies.generator
        if generator is not None:
            return generator
        raise ServiceUnavailableError("Generation backend is not configured")

    def _request_id(self) -> str:
        return uuid4().hex

    def _job_id(self) -> str:
        return uuid4().hex

    def _idempotent_job(self, *, idempotency_key: str | None):
        if idempotency_key is None:
            return None
        return self.dependencies.ingest_job_manager.idempotent_job(
            idempotency_key=idempotency_key
        )

    def _ingest_response(
        self,
        *,
        request_id: str,
        job,
    ) -> IngestResponse:
        return IngestResponse(request_id=request_id, job=job, summary=job.summary)

    def _require_job(self, *, job_id: str):
        job = self.dependencies.ingest_job_manager.get(job_id=job_id)
        if job is None:
            raise ValueError(f"Unknown ingest job: {job_id}")
        return job

    def _replay_paths(self, *, source, mode: str) -> list[str]:
        summary = source.summary
        if mode == "all":
            return list(source.paths)
        if summary is None:
            return list(source.paths)
        return [
            result.path
            for result in summary.document_results
            if result.status in {"failed", "quarantined"}
        ]

    def _resolve_document(self, *, document: str) -> Path:
        resolved = (self.ingest_root / document).resolve()
        if not self._within_ingest_root(path=resolved):
            raise ValueError("document reference escapes INGEST_INPUT_DIR")
        if not resolved.exists() or not resolved.is_file():
            raise ValueError(f"Unknown ingest document: {document}")
        return resolved

    def _within_ingest_root(self, *, path: Path) -> bool:
        try:
            path.relative_to(self.ingest_root)
        except ValueError:
            return False
        return True
