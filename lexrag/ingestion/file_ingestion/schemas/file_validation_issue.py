"""Schema for granular file validation findings."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FileValidationIssue(BaseModel):
    """One structured validation finding emitted by the validator."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(description="Stable machine-readable validation code.")
    message: str = Field(description="Human-readable description of the issue.")
    severity: Literal["warning", "error"] = Field(
        description="Severity surfaced to callers and operators."
    )
    blocking: bool = Field(
        description="Whether this issue should prevent the file from being parsed."
    )
