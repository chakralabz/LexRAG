"""SDK-facing file-type selection config for file ingestion."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .supported_file_type import SupportedFileType


class FileTypeSelectionConfig(BaseModel):
    """Describe which file types the ingestion SDK should accept."""

    model_config = ConfigDict(frozen=True)

    allowed_file_types: tuple[SupportedFileType, ...] = Field(
        default=tuple(SupportedFileType),
        description="Concrete file formats accepted by the ingestion boundary.",
    )

    @field_validator("allowed_file_types")
    @classmethod
    def _validate_allowed_file_types(
        cls,
        value: tuple[SupportedFileType, ...],
    ) -> tuple[SupportedFileType, ...]:
        """Ensure the configured file-type list is usable.

        Args:
            value: Allowed file types provided by the caller.

        Returns:
            Deduplicated tuple of allowed file types in caller order.
        """
        deduplicated = tuple(dict.fromkeys(value))
        if not deduplicated:
            raise ValueError("At least one allowed file type must be configured.")
        return deduplicated
