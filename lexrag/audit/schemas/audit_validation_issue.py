"""Schema describing one audit validation failure."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AuditValidationIssue(BaseModel):
    """Capture one missing or invalid audit field.

    Attributes:
        subject_id: Stable chunk or record identifier under validation.
        field_name: Field that violated the audit contract.
        owner: Layer expected to populate the field.
        reason: Human-readable explanation for the violation.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    subject_id: str = Field(min_length=1)
    field_name: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    reason: str = Field(min_length=1)
