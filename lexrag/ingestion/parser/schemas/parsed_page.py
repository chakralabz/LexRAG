"""Legacy parsed page DTO kept for compatibility tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ParsedPage:
    """Historic page-level parser DTO.

    New code should prefer ``ParsedBlock``. This type remains because some
    compatibility tests intentionally feed legacy parser outputs into the
    orchestration layer.
    """

    page: int
    section: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return the historic dictionary representation."""
        return {
            "page": self.page,
            "section": self.section,
            "text": self.text,
            "metadata": self.metadata,
        }
