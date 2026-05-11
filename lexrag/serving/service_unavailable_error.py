"""Serving-layer error raised when a dependency is not production-ready."""

from __future__ import annotations

from lexrag.utils.lexrag_error import LexRAGError


class ServiceUnavailableError(LexRAGError):
    """Raised when the serving layer is alive but not ready for traffic."""
