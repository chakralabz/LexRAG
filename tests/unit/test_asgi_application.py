from __future__ import annotations

import asyncio
import json
from pathlib import Path

from lexrag.context_builder import LLMContextBuilder
from lexrag.ingestion.jobs import IngestJobManager, IngestJobRepository
from lexrag.serving.asgi_application import LexRAGASGIApplication
from lexrag.serving.fixed_window_rate_limiter import FixedWindowRateLimiter
from lexrag.serving.lexrag_application import LexRAGApplication
from lexrag.serving.request_authorizer import RequestAuthorizer
from lexrag.serving.runtime_dependencies import RuntimeDependencies


class FakePipeline:
    def ingest_documents(self, paths: list) -> object:
        _ = paths
        raise AssertionError("ingest should not run in this test")


class FakeRetriever:
    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        metadata_filters: dict | None = None,
    ) -> list:
        _ = query, top_k, metadata_filters
        return []


class FakeContextBuilder:
    def build(self, *, query: str, chunks: list, document_catalog=None) -> object:
        _ = query, chunks, document_catalog
        raise AssertionError("query should not run in this test")


def test_protected_routes_require_authorization(tmp_path: Path) -> None:
    app = _asgi_app(tmp_path, api_secret_key="secret")

    response = _invoke(app, method="GET", path="/ingest/jobs/missing")

    assert response["status"] == 401
    assert response["payload"]["error"] == "missing_authorization"


def test_http_ingest_returns_forbidden_when_disabled(tmp_path: Path) -> None:
    app = _asgi_app(tmp_path, api_secret_key="secret")

    response = _invoke(
        app,
        method="POST",
        path="/ingest",
        headers={"authorization": "Bearer secret"},
        payload={"documents": ["a.pdf"]},
    )

    assert response["status"] == 403
    assert response["payload"]["error"] == "http_ingest_disabled"


def test_rate_limit_returns_too_many_requests(tmp_path: Path) -> None:
    app = _asgi_app(tmp_path, api_secret_key="secret", rate_limit=1)

    first = _invoke(
        app,
        method="GET",
        path="/ingest/jobs/missing",
        headers={"authorization": "Bearer secret"},
    )
    second = _invoke(
        app,
        method="GET",
        path="/ingest/jobs/missing",
        headers={"authorization": "Bearer secret"},
    )

    assert first["status"] == 404
    assert second["status"] == 429
    assert second["payload"]["error"] == "rate_limit_exceeded"


def _asgi_app(
    tmp_path: Path,
    *,
    api_secret_key: str,
    rate_limit: int = 5,
) -> LexRAGASGIApplication:
    ingest_root = tmp_path / "ingest"
    ingest_root.mkdir()
    (ingest_root / "a.pdf").write_text("sample", encoding="utf-8")
    manager = IngestJobManager(
        repository=IngestJobRepository(root_dir=tmp_path / "jobs")
    )
    application = LexRAGApplication(
        dependencies=RuntimeDependencies(
            ingestion_pipeline=FakePipeline(),  # type: ignore[arg-type]
            ingest_job_manager=manager,
            retriever=FakeRetriever(),  # type: ignore[arg-type]
            context_builder=LLMContextBuilder(),
            generator=None,
        ),
        ingest_root=ingest_root,
        http_ingest_enabled=False,
    )
    return LexRAGASGIApplication(
        application=application,
        authorizer=RequestAuthorizer(api_secret_key=api_secret_key),
        rate_limiter=FixedWindowRateLimiter(limit=rate_limit),
    )


def _invoke(
    app: LexRAGASGIApplication,
    *,
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return asyncio.run(
        _invoke_async(
            app,
            method=method,
            path=path,
            headers=headers,
            payload=payload,
        )
    )


async def _invoke_async(
    app: LexRAGASGIApplication,
    *,
    method: str,
    path: str,
    headers: dict[str, str] | None,
    payload: dict[str, object] | None,
) -> dict[str, object]:
    body = _body(payload=payload)
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": _headers(headers=headers, body=body),
        "client": ("127.0.0.1", 8000),
    }
    messages: list[dict[str, object]] = []
    body_sent = False

    async def receive() -> dict[str, object]:
        nonlocal body_sent
        if body_sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        body_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    await app(scope, receive, send)
    return _response(messages=messages)


def _body(payload: dict[str, object] | None) -> bytes:
    if payload is None:
        return b""
    return json.dumps(payload).encode("utf-8")


def _headers(*, headers: dict[str, str] | None, body: bytes) -> list[tuple[bytes, bytes]]:
    encoded = [(b"content-length", str(len(body)).encode("ascii"))]
    for name, value in (headers or {}).items():
        encoded.append((name.encode("latin-1"), value.encode("latin-1")))
    return encoded


def _response(*, messages: list[dict[str, object]]) -> dict[str, object]:
    status = 0
    body = b""
    for message in messages:
        if message["type"] == "http.response.start":
            status = int(message["status"])
        if message["type"] == "http.response.body":
            body = bytes(message.get("body", b""))
    return {"status": status, "payload": json.loads(body.decode("utf-8"))}
