"""Schema describing audit validation outcome for one subject."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.audit.schemas.audit_validation_issue import AuditValidationIssue


class AuditValidationResult(BaseModel):
    """Summarize validation results for one chunk or audit subject.

    Attributes:
        subject_id: Stable identifier of the validated subject.
        passed: Whether the subject satisfied all required fields.
        completeness_score: Fraction of requirements satisfied in `[0, 1]`.
        issues: Ordered list of missing-field issues.
    """

    model_config = ConfigDict(frozen=True)

    subject_id: str = Field(min_length=1)
    passed: bool
    completeness_score: float = Field(ge=0.0, le=1.0)
    issues: list[AuditValidationIssue] = Field(default_factory=list)
