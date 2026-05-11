"""Public parser service with explicit lifecycle management."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from lexrag.ingestion.parser import (
    DocumentParseResult,
    DocumentParserProtocol,
    FallbackDocumentParser,
    ParsedBlock,
)
from lexrag.runtime import ManagedResource


class ParserService:
    """Manage parser initialization for startup-time or lazy reuse."""

    def __init__(
        self,
        *,
        parser_factory: Callable[[], DocumentParserProtocol] | None = None,
        finalizer: Callable[[DocumentParserProtocol], None] | None = None,
    ) -> None:
        factory = parser_factory or _build_parser
        self._resource = ManagedResource(loader=factory, finalizer=finalizer)

    @property
    def loaded(self) -> bool:
        """Return whether the parser runtime has been initialized."""
        return self._resource.loaded

    def load(self) -> ParserService:
        """Initialize the parser runtime and return this service."""
        self._resource.load()
        return self

    def close(self) -> None:
        """Release the cached parser runtime."""
        self._resource.close()

    def parse_document(self, path: str | Path) -> list[ParsedBlock]:
        """Parse one document into canonical parsed blocks."""
        parser = self._resource.get()
        return parser.parse_document(path)

    def parse_with_report(self, path: str | Path) -> DocumentParseResult:
        """Parse one document and return the full parse report."""
        parser = self._resource.get()
        return parser.parse_with_report(path)


def _build_parser() -> DocumentParserProtocol:
    """Build the default architecture-compliant parser runtime."""
    return FallbackDocumentParser()
