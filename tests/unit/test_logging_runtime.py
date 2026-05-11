from __future__ import annotations

import io
import json

from lexrag.observability import configure_logging, get_logger, request_context
from lexrag.observability.schemas import LoggingConfig


def test_configure_logging_emits_structured_json_with_request_context() -> None:
    stream = io.StringIO()
    configure_logging(
        LoggingConfig(level="INFO", fmt="json"),
        force=True,
        stream=stream,
    )
    logger = get_logger("lexrag.test")

    with request_context("req-123"):
        logger.info(
            "parsed document",
            extra={"component": "parser", "metric_name": "parser_success_rate"},
        )

    payload = json.loads(stream.getvalue().strip())
    assert payload["request_id"] == "req-123"
    assert payload["component"] == "parser"
    assert payload["metric_name"] == "parser_success_rate"
    assert payload["message"] == "parsed document"
