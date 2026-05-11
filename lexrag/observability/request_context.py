"""Request-scoped logging context helpers."""

from __future__ import annotations

import contextvars
from collections.abc import Generator
from contextlib import contextmanager

from lexrag.observability.request_context_filter import RequestContextFilter

_request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "lexrag_request_id",
    default=None,
)


def set_request_id(value: str | None) -> contextvars.Token[str | None]:
    """Set the request ID for the current execution context."""
    return _request_id_ctx.set(value)


def get_request_id() -> str | None:
    """Return the request ID for the current execution context."""
    return _request_id_ctx.get()


@contextmanager
def request_context(request_id: str | None) -> Generator[None]:
    """Apply a request ID to a scoped block of work."""
    token = set_request_id(request_id)
    try:
        yield
    finally:
        _request_id_ctx.reset(token)


def request_context_filter() -> RequestContextFilter:
    """Create a logging filter bound to the shared request context."""
    return RequestContextFilter(request_id_ctx=_request_id_ctx)
