"""Schema for file validation results."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .antivirus_scan_result import AntivirusScanResult
from .file_validation_issue import FileValidationIssue


class FileValidationResult(BaseModel):
    """Structured output from the file validation layer."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(description="Resolved file path as a string for audit logging.")
    extension: str = Field(description="Normalized file extension.")
    file_size_bytes: int = Field(ge=0, description="Document size in bytes.")
    page_count: int | None = Field(
        default=None,
        ge=0,
        description="Detected page count for paged formats when available.",
    )
    media_type: str = Field(description="Detected MIME-like content type.")
    sha256: str = Field(
        description="Stable file hash used for deduplication and audits."
    )
    encrypted: bool = Field(description="Whether the document appears encrypted.")
    corrupted: bool = Field(description="Whether lightweight integrity checks failed.")
    supported_extension: bool = Field(
        description="Whether the extension is allowlisted."
    )
    extension_matches_media_type: bool = Field(
        description="Whether the extension aligns with detected content type."
    )
    duplicate_in_batch: bool = Field(
        description="Whether the same content already appeared in the current batch."
    )
    antivirus: AntivirusScanResult = Field(
        description="Malware scan result attached for operational observability."
    )
    issues: list[FileValidationIssue] = Field(
        description="Ordered validation findings with blocking and warning semantics."
    )
    is_valid: bool = Field(description="Whether parsing is permitted to continue.")
    failure_reason: str | None = Field(
        default=None,
        description="Primary blocking issue code when the file is rejected.",
    )
