"""Transition adapter from file ingestion into document parsing."""

from __future__ import annotations

from lexrag.ingestion.file_ingestion import FileLoadResult
from lexrag.ingestion.parser.orchestration.manual_recovery_required_error import (
    ManualRecoveryRequiredError,
)
from lexrag.ingestion.parser.orchestration.document_parser import DocumentParser
from lexrag.ingestion.parser.schemas.loaded_document_parse_result import (
    LoadedDocumentParseResult,
)
from lexrag.ingestion.parser.schemas.loaded_document_parse_status import (
    LoadedDocumentParseStatus,
)


class LoadedDocumentParserPipeline:
    """Consume file-ingestion outputs and execute document parsing."""

    def __init__(
        self,
        *,
        parser: DocumentParser | None = None,
    ) -> None:
        """Initialize the transition adapter from file ingestion to parsing."""
        self.parser = parser or DocumentParser()

    def parse_loaded_file(
        self, load_result: FileLoadResult
    ) -> LoadedDocumentParseResult:
        """Parse one file that has already been approved by file ingestion."""
        return self._parse_loaded_file(load_result=load_result)

    def parse_loaded_files(
        self,
        load_results: list[FileLoadResult],
    ) -> list[LoadedDocumentParseResult]:
        """Parse a batch of file-ingestion outputs in order."""
        return [self._parse_loaded_file(load_result=item) for item in load_results]

    def _parse_loaded_file(
        self, *, load_result: FileLoadResult
    ) -> LoadedDocumentParseResult:
        """Parse one validated load result into a terminal parser status."""
        if not load_result.is_ready:
            return self._rejected_result(load_result=load_result)
        try:
            document_parse_result = self.parser.parse_loaded_file(load_result)
        except ManualRecoveryRequiredError as exc:
            return self._error_result(
                load_result=load_result,
                status=LoadedDocumentParseStatus.QUARANTINED,
                error=exc,
            )
        except Exception as exc:
            return self._error_result(
                load_result=load_result,
                status=LoadedDocumentParseStatus.FAILED,
                error=exc,
            )
        return LoadedDocumentParseResult(
            file_load_result=load_result,
            document_parse_result=document_parse_result,
            status=LoadedDocumentParseStatus.PARSED,
        )

    def _rejected_result(
        self, *, load_result: FileLoadResult
    ) -> LoadedDocumentParseResult:
        """Convert upstream file-loader rejection into a parser terminal result."""
        return LoadedDocumentParseResult(
            file_load_result=load_result,
            document_parse_result=None,
            status=LoadedDocumentParseStatus.REJECTED,
            error_type=load_result.rejection_reason,
            error_message=load_result.failure_message,
        )

    def _error_result(
        self,
        *,
        load_result: FileLoadResult,
        status: LoadedDocumentParseStatus,
        error: Exception,
    ) -> LoadedDocumentParseResult:
        """Translate parser exceptions into a stable structured result."""
        return LoadedDocumentParseResult(
            file_load_result=load_result,
            document_parse_result=None,
            status=status,
            error_type=error.__class__.__name__,
            error_message=str(error),
        )
