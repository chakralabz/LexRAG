"""Build stable structured validation issues from policy codes."""

from __future__ import annotations

from lexrag.ingestion.file_ingestion.schemas.file_ingestion_config import (
    FileIngestionConfig,
)
from lexrag.ingestion.file_ingestion.schemas.file_validation_issue import (
    FileValidationIssue,
)


class ValidationIssueFactory:
    """Create validation issues with centrally managed messages."""

    def __init__(self, config: FileIngestionConfig | None = None) -> None:
        """Store the message catalog used for issue creation.

        Args:
            config: Optional shared ingestion configuration.
        """
        self.config = config or FileIngestionConfig()

    def build(self, code: str, *, blocking: bool) -> FileValidationIssue:
        """Return a canonical validation issue for a policy violation.

        Args:
            code: Stable validation issue code.
            blocking: Whether the issue should block ingestion.

        Returns:
            Canonical structured validation issue.
        """
        return FileValidationIssue(
            code=code,
            message=self.config.validation_messages[code],
            severity="error" if blocking else "warning",
            blocking=blocking,
        )
