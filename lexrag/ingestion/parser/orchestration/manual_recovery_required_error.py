"""Errors raised when a document must be quarantined for manual recovery."""

from __future__ import annotations

from lexrag.ingestion.parser.schemas.document_parse_result import DocumentParseResult
from lexrag.utils.lexrag_error import LexRAGError


class ManualRecoveryRequiredError(LexRAGError):
    """Raised when every parser strategy has been exhausted."""

    def __init__(self, message: str, *, result: DocumentParseResult) -> None:
        """Store the parse report alongside the domain error.

        Args:
            message: Human-readable error message.
            result: Structured parse report describing what failed.
        """
        super().__init__(message, details=result.model_dump())
        self.result = result
