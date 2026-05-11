"""Base domain error type for LexRAG."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class LexRAGError(Exception):
    """Base error for domain-specific failures."""

    def __init__(
        self,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = dict(details or {})
