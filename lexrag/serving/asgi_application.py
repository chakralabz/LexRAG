"""ASGI application for LexRAG serving routes."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Any

from pydantic import ValidationError

from lexrag.observability.logging_runtime import get_logger
from lexrag.serving.fixed_window_rate_limiter import FixedWindowRateLimiter
from lexrag.serving.lexrag_application import LexRAGApplication
from lexrag.serving.request_authorizer import RequestAuthorizer
from lexrag.serving.schemas import IngestReplayRequest, IngestRequest, QueryRequest
from lexrag.serving.service_unavailable_error import ServiceUnavailableError

logger = get_logger(__name__)
ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]


class LexRAGASGIApplication:
    """Route authenticated JSON HTTP requests into the serving application."""

    def __init__(
        self,
        *,
        application: LexRAGApplication,
        authorizer: RequestAuthorizer,
        rate_limiter: FixedWindowRateLimiter,
    ) -> None:
        self.application = application
        self.authorizer = authorizer
        self.rate_limiter = rate_limiter

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: ASGIReceive,
        send: ASGISend,
    ) -> None:
        if scope.get("type") != "http":
            raise RuntimeError("LexRAGASGIApplication only supports HTTP")
        await self._handle_http(scope=scope, receive=receive, send=send)

    async def _handle_http(
        self,
        *,
        scope: dict[str, Any],
        receive: ASGIReceive,
        send: ASGISend,
    ) -> None:
        path = str(scope.get("path", "/"))
        headers = _decode_headers(scope=scope)
        try:
            self.authorizer.authorize(path=path, headers=headers)
            self._enforce_rate_limit(path=path, headers=headers, scope=scope)
            status, payload = await self._dispatch(
                method=str(scope.get("method", "GET")),
                path=path,
                headers=headers,
                receive=receive,
            )
        except Exception as exc:
            status, payload = self._error_response(exc=exc)
        await self._write_json(send=send, status=status, payload=payload)

    async def _dispatch(
        self,
        *,
        method: str,
        path: str,
        headers: dict[str, str],
        receive: ASGIReceive,
    ) -> tuple[HTTPStatus, dict[str, object]]:
        if method == "GET":
            return self._dispatch_get(path=path)
        if method == "POST":
            payload = await self._json_body(receive=receive)
            return self._dispatch_post(path=path, headers=headers, payload=payload)
        return HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"}

    def _dispatch_get(self, *, path: str) -> tuple[HTTPStatus, dict[str, object]]:
        if path == "/health":
            return HTTPStatus.OK, self.application.health().model_dump(mode="json")
        if path == "/ready":
            readiness = self.application.readiness()
            status = HTTPStatus.OK if readiness.ready else HTTPStatus.SERVICE_UNAVAILABLE
            return status, readiness.model_dump(mode="json")
        if path.startswith("/ingest/jobs/"):
            return self._ingest_job(path=path)
        return HTTPStatus.NOT_FOUND, {"error": "not_found"}

    def _dispatch_post(
        self,
        *,
        path: str,
        headers: dict[str, str],
        payload: dict[str, object],
    ) -> tuple[HTTPStatus, dict[str, object]]:
        request_id = _request_id(headers=headers)
        if path == "/ingest":
            return self._ingest(payload=payload, request_id=request_id)
        if path.startswith("/ingest/jobs/") and path.endswith("/replay"):
            return self._replay(path=path, payload=payload, request_id=request_id)
        if path == "/query":
            return self._query(payload=payload, request_id=request_id)
        return HTTPStatus.NOT_FOUND, {"error": "not_found"}

    async def _json_body(self, *, receive: ASGIReceive) -> dict[str, object]:
        body = await _read_body(receive=receive)
        if not body:
            return {}
        parsed = json.loads(body.decode("utf-8"))
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("Request body must be a JSON object")

    def _ingest(
        self,
        *,
        payload: dict[str, object],
        request_id: str | None,
    ) -> tuple[HTTPStatus, dict[str, object]]:
        request = IngestRequest.model_validate(payload)
        result = self.application.ingest(request, request_id=request_id)
        return HTTPStatus.OK, result.model_dump(mode="json")

    def _query(
        self,
        *,
        payload: dict[str, object],
        request_id: str | None,
    ) -> tuple[HTTPStatus, dict[str, object]]:
        request = QueryRequest.model_validate(payload)
        result = self.application.query(request, request_id=request_id)
        return HTTPStatus.OK, result.model_dump(mode="json")

    def _ingest_job(self, *, path: str) -> tuple[HTTPStatus, dict[str, object]]:
        job_id = path.removeprefix("/ingest/jobs/").strip()
        if not job_id:
            return HTTPStatus.BAD_REQUEST, {"error": "missing_job_id"}
        try:
            result = self.application.ingest_job(job_id=job_id)
        except ValueError as exc:
            return HTTPStatus.NOT_FOUND, {"error": str(exc)}
        return HTTPStatus.OK, result.model_dump(mode="json")

    def _replay(
        self,
        *,
        path: str,
        payload: dict[str, object],
        request_id: str | None,
    ) -> tuple[HTTPStatus, dict[str, object]]:
        job_id = path.removeprefix("/ingest/jobs/").removesuffix("/replay").strip()
        if not job_id:
            return HTTPStatus.BAD_REQUEST, {"error": "missing_job_id"}
        request = IngestReplayRequest.model_validate(payload)
        result = self.application.replay_ingest_job(
            job_id=job_id,
            request=request,
            request_id=request_id,
        )
        return HTTPStatus.OK, result.model_dump(mode="json")

    def _enforce_rate_limit(
        self,
        *,
        path: str,
        headers: dict[str, str],
        scope: dict[str, Any],
    ) -> None:
        if path in {"/health", "/ready"}:
            return
        key = _rate_limit_key(headers=headers, scope=scope)
        if self.rate_limiter.allow(key=key):
            return
        raise PermissionError("rate_limit_exceeded")

    def _error_response(self, *, exc: Exception) -> tuple[HTTPStatus, dict[str, object]]:
        if isinstance(exc, ValidationError):
            return HTTPStatus.BAD_REQUEST, {"error": exc.errors()}
        if isinstance(exc, ValueError):
            return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
        if isinstance(exc, ServiceUnavailableError):
            return self._service_unavailable(exc=exc)
        if isinstance(exc, PermissionError):
            return self._permission_denied(exc=exc)
        logger.exception("Serving request failed", exc_info=exc)
        return HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal_server_error"}

    def _service_unavailable(
        self,
        *,
        exc: ServiceUnavailableError,
    ) -> tuple[HTTPStatus, dict[str, object]]:
        return (
            HTTPStatus.SERVICE_UNAVAILABLE,
            {"error": exc.message, "details": exc.details},
        )

    def _permission_denied(
        self,
        *,
        exc: PermissionError,
    ) -> tuple[HTTPStatus, dict[str, object]]:
        error = str(exc)
        if error == "rate_limit_exceeded":
            return HTTPStatus.TOO_MANY_REQUESTS, {"error": error}
        status = HTTPStatus.UNAUTHORIZED if "authorization" in error else HTTPStatus.FORBIDDEN
        return status, {"error": error}

    async def _write_json(
        self,
        *,
        send: ASGISend,
        status: HTTPStatus,
        payload: dict[str, object],
    ) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status.value,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(encoded)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": encoded})


def _decode_headers(*, scope: dict[str, Any]) -> dict[str, str]:
    decoded: dict[str, str] = {}
    for name, value in scope.get("headers", []):
        decoded[name.decode("latin-1").lower()] = value.decode("latin-1")
    return decoded


async def _read_body(*, receive: ASGIReceive) -> bytes:
    parts: list[bytes] = []
    more_body = True
    while more_body:
        message = await receive()
        parts.append(message.get("body", b""))
        more_body = bool(message.get("more_body", False))
    return b"".join(parts)


def _request_id(*, headers: dict[str, str]) -> str | None:
    value = headers.get("x-request-id")
    if value is None:
        return None
    return value.strip() or None


def _rate_limit_key(*, headers: dict[str, str], scope: dict[str, Any]) -> str:
    authorization = headers.get("authorization")
    if authorization:
        return authorization
    client = scope.get("client")
    if isinstance(client, tuple) and client:
        return str(client[0])
    return "anonymous"
