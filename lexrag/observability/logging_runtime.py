"""Runtime logging configuration for LexRAG services."""

from __future__ import annotations

import logging
import sys
from typing import TextIO

from lexrag.config import get_settings
from lexrag.observability.json_log_formatter import JsonLogFormatter
from lexrag.observability.request_context import request_context_filter
from lexrag.observability.schemas import LoggingConfig

_DEFAULT_LOGGER_NAME = "lexrag"
_SUPPORTED_FORMATS = frozenset({"text", "json"})
_configured = False


def configure_logging(
    config: LoggingConfig | None = None,
    *,
    force: bool = False,
    stream: TextIO | None = None,
) -> None:
    """Configure the process root logger with LexRAG defaults."""
    global _configured
    resolved = config or _config_from_settings()
    _validate_log_format(config=resolved)
    root_logger = logging.getLogger()
    if _configured and not force:
        return
    if force:
        _reset_handlers(root_logger=root_logger)
    root_logger.setLevel(_resolve_level(level=resolved.level))
    root_logger.addHandler(_build_handler(config=resolved, stream=stream))
    _configured = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a namespaced logger for the provided module."""
    return logging.getLogger(name or _DEFAULT_LOGGER_NAME)


def _config_from_settings() -> LoggingConfig:
    settings = get_settings()
    return LoggingConfig(
        level=settings.LEXRAG_LOG_LEVEL, fmt=settings.LEXRAG_LOG_FORMAT
    )


def _validate_log_format(*, config: LoggingConfig) -> None:
    if config.fmt in _SUPPORTED_FORMATS:
        return
    raise ValueError(f"Unsupported log format: {config.fmt!r}")


def _resolve_level(*, level: str) -> int:
    resolved = logging.getLevelName(level.upper())
    if isinstance(resolved, str):
        raise ValueError(f"Unsupported log level: {level!r}")
    return resolved


def _reset_handlers(*, root_logger: logging.Logger) -> None:
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)


def _build_handler(
    *,
    config: LoggingConfig,
    stream: TextIO | None,
) -> logging.Handler:
    handler = logging.StreamHandler(stream=stream or sys.stdout)
    handler.addFilter(request_context_filter())
    handler.setFormatter(_formatter(config=config))
    return handler


def _formatter(*, config: LoggingConfig) -> logging.Formatter:
    if config.fmt == "json":
        return JsonLogFormatter()
    return logging.Formatter(
        fmt=(
            "%(asctime)s %(levelname)s %(name)s [request_id=%(request_id)s] %(message)s"
        ),
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
