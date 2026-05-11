"""Configuration-specific exception type."""

from __future__ import annotations

from lexrag.utils.lexrag_error import LexRAGError


class ConfigurationError(LexRAGError):
    """Raised when required configuration is missing or invalid."""
