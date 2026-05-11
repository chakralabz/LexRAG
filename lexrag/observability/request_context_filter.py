"""Logging filter that injects request-scoped context fields."""

from __future__ import annotations

import contextvars
import logging


class RequestContextFilter(logging.Filter):
    """Attach request identifiers from `contextvars` to log records."""

    def __init__(self, *, request_id_ctx: contextvars.ContextVar[str | None]) -> None:
        super().__init__()
        self._request_id_ctx = request_id_ctx

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = self._request_id_ctx.get() or "-"
        return True
