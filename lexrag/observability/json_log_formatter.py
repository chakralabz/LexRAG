"""JSON formatter for production log pipelines."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

_RESERVED_FIELDS = frozenset(logging.makeLogRecord({}).__dict__)


class JsonLogFormatter(logging.Formatter):
    """Render logs as structured JSON with stable core fields.

    The formatter preserves standard fields for searchability and also forwards
    non-standard `extra=` payloads so application layers can annotate events
    with domain metadata such as component, metric, or document identifiers.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = self._base_payload(record=record)
        payload.update(self._extra_payload(record=record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)

    def _base_payload(self, *, record: logging.LogRecord) -> dict[str, object]:
        return {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "module": record.module,
            "line": record.lineno,
        }

    def _extra_payload(self, *, record: logging.LogRecord) -> dict[str, object]:
        payload: dict[str, object] = {}
        for key, value in record.__dict__.items():
            if key in _RESERVED_FIELDS or key == "message":
                continue
            payload[key] = value
        return payload
