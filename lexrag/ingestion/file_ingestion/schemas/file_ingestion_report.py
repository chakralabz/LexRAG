"""Combined report for the file ingestion gateway."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .file_type_detection import FileTypeDetection
from .file_validation_result import FileValidationResult


class FileIngestionReport(BaseModel):
    """Full pre-parse inspection result for one document."""

    model_config = ConfigDict(frozen=True)

    validation: FileValidationResult = Field(
        description="Validation outcome from architecture layer 2.1."
    )
    detection: FileTypeDetection = Field(
        description="Type detection outcome from architecture layer 2.2."
    )
