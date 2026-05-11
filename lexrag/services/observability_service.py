"""Public observability service for logging, metrics, and tracing hooks."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from lexrag.observability import (
    LoggingConfig,
    configure_logging,
    get_logger,
    request_context,
)


class ObservabilityService:
    """Provide structured package-level observability hooks."""

    def __init__(
        self,
        *,
        logging_config: LoggingConfig | None = None,
        metrics_hook: Callable[[str, float, dict[str, str]], None] | None = None,
        trace_hook: Callable[[str, dict[str, Any]], None] | None = None,
        audit_hook: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self._logging_config = logging_config
        self._metrics_hook = metrics_hook
        self._trace_hook = trace_hook
        self._audit_hook = audit_hook
        self._logger = get_logger(__name__)

    def configure(self, *, force: bool = False) -> None:
        """Configure logging for package consumers."""
        configure_logging(config=self._logging_config, force=force)

    def request_scope(self, request_id: str | None) -> AbstractContextManager[None]:
        """Return a context manager that propagates request metadata."""
        return request_context(request_id)

    def record_metric(
        self,
        name: str,
        value: float,
        *,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Emit one metric to the configured metrics sink."""
        if self._metrics_hook is None:
            return
        self._metrics_hook(name, value, tags or {})

    def record_event(
        self,
        name: str,
        *,
        metadata: dict[str, Any] | None = None,
        audit_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Emit one structured event to logging and external hooks."""
        payload = {"event": name, "metadata": metadata or {}}
        if audit_metadata is not None:
            payload["audit"] = audit_metadata
        self._logger.info("lexrag_event=%s", payload)
        self._emit_trace(name=name, payload=payload)
        self._emit_audit(name=name, payload=payload)

    def _emit_trace(self, *, name: str, payload: dict[str, Any]) -> None:
        if self._trace_hook is not None:
            self._trace_hook(name, payload)

    def _emit_audit(self, *, name: str, payload: dict[str, Any]) -> None:
        if self._audit_hook is not None:
            self._audit_hook(name, payload)
