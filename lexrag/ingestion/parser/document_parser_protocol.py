"""Runtime contract for ingestion-facing document parsers.

The ingestion pipeline depends on behavior, not on the concrete orchestrator
class. Keeping this protocol small makes it easy to substitute test doubles or
future parser orchestrators without widening the integration surface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from lexrag.ingestion.parser.schemas.document_parse_result import DocumentParseResult
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


@runtime_checkable
class DocumentParserProtocol(Protocol):
    """Define the parser capabilities required by the ingestion pipeline."""

    def parse_document(self, path: str | Path) -> list[ParsedBlock]:
        """Parse a document into canonical blocks."""

    def parse_with_report(self, path: str | Path) -> DocumentParseResult:
        """Parse a document and return structured provenance metadata."""
