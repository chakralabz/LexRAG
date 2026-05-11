"""Observability surface for logging, request tracing, and monitoring."""

from lexrag.observability.logging_runtime import configure_logging, get_logger
from lexrag.observability.monitoring_catalog import MonitoringCatalog
from lexrag.observability.request_context import (
    get_request_id,
    request_context,
    set_request_id,
)
from lexrag.observability.schemas import (
    AlertThreshold,
    LoggingConfig,
    MetricDefinition,
)

__all__ = [
    "AlertThreshold",
    "LoggingConfig",
    "MetricDefinition",
    "MonitoringCatalog",
    "configure_logging",
    "get_logger",
    "get_request_id",
    "request_context",
    "set_request_id",
]
