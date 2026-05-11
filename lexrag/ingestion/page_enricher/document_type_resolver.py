"""Document type resolver protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class DocumentTypeResolver(Protocol):
    """Resolves canonical document type for a source path."""

    def resolve(self, *, path: Path) -> str:
        """Return canonical document type label used in chunk metadata."""
        ...
