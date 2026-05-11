"""Schema for loaded-document parser results."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.ingestion.file_ingestion.schemas.file_load_result import FileLoadResult

from .document_parse_result import DocumentParseResult
from .loaded_document_parse_status import LoadedDocumentParseStatus


class LoadedDocumentParseResult(BaseModel):
    """Describe the parser-stage outcome for one loaded document."""

    model_config = ConfigDict(frozen=True)

    file_load_result: FileLoadResult = Field(
        description="Structured load result produced by the file-ingestion boundary."
    )
    document_parse_result: DocumentParseResult | None = Field(
        default=None,
        description="Structured parse result when the file reached parser execution.",
    )
    status: LoadedDocumentParseStatus = Field(
        description="Terminal status such as parsed, rejected, failed, or quarantined."
    )
    error_type: str | None = Field(
        default=None,
        description="Exception type captured when parsing failed after loading.",
    )
    error_message: str | None = Field(
        default=None,
        description="Human-readable parse failure detail when available.",
    )
