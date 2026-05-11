"""Static document type resolver."""

from __future__ import annotations

from pathlib import Path


class StaticDocumentTypeResolver:
    """Always returns one configured document type."""

    def __init__(self, *, doc_type: str) -> None:
        self.doc_type = doc_type.strip() or "unknown"

    def resolve(self, *, path: Path) -> str:
        """Return configured type regardless of path."""
        _ = path
        return self.doc_type
