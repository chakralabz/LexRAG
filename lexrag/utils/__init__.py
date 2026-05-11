"""Shared utility helpers for LexRAG services and pipelines."""

from lexrag.utils.cli import (
    add_optional_limit_args,
    positive_int,
    resolve_optional_limit,
)
from lexrag.observability.logging_runtime import configure_logging, get_logger
from lexrag.observability.request_context import get_request_id, request_context
from lexrag.observability.schemas.logging_config import LoggingConfig as LoggingSettings
from lexrag.utils.configuration_error import ConfigurationError
from lexrag.utils.env import get_env_bool, get_env_float, get_env_int, get_env_str
from lexrag.utils.lexrag_error import LexRAGError
from lexrag.utils.retry import retry
from lexrag.utils.text import TextNormalizer
from lexrag.utils.timing import log_duration, timed

__all__ = [
    "ConfigurationError",
    "LexRAGError",
    "LoggingSettings",
    "TextNormalizer",
    "add_optional_limit_args",
    "configure_logging",
    "get_env_bool",
    "get_env_float",
    "get_env_int",
    "get_env_str",
    "get_logger",
    "get_request_id",
    "log_duration",
    "positive_int",
    "request_context",
    "resolve_optional_limit",
    "retry",
    "timed",
]
