"""Contracts for parser backends.

Backends are intentionally simple: each parser knows how to turn a path into
parsed blocks, while orchestration lives in ``DocumentParser``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class BaseDocumentParser(ABC):
    """Abstract parser backend contract.

    Concrete parsers implement one extraction strategy, such as Docling or
    PyMuPDF. They do not decide when they should run; the orchestrator owns
    selection and fallback policy.
    """

    @property
    def parser_name(self) -> str:
        """Return the stable parser identifier used in provenance metadata."""
        return self.__class__.__name__.removesuffix("Parser").lower()

    @abstractmethod
    def parse(self, path: Path) -> list[ParsedBlock]:
        """Extract parsed blocks from a document path.

        Args:
            path: Absolute or relative path to a source document.

        Returns:
            Canonical parsed blocks extracted from the document.

        Raises:
            FileNotFoundError: If the input path does not exist.
            RuntimeError: If the parser cannot extract usable content.
        """
