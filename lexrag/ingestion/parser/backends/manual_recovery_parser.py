"""Manual recovery backend.

This backend does not parse documents. Its job is to make the terminal state of
the fallback chain explicit.
"""

from __future__ import annotations

from pathlib import Path

from lexrag.ingestion.parser.backends.base_document_parser import BaseDocumentParser
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class ManualRecoveryParser(BaseDocumentParser):
    """Terminal backend used when automated parsing is exhausted."""

    def parse(self, path: Path) -> list[ParsedBlock]:
        """Raise a terminal manual-recovery error.

        Args:
            path: Document path that requires quarantine.

        Returns:
            This method never returns because manual recovery is terminal.
        """
        raise RuntimeError(f"Manual recovery required for document: {path}")
