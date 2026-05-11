"""Schema describing one audit metadata requirement."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AuditRequirement(BaseModel):
    """Describe one architecture-mandated field for audit completeness.

    Attributes:
        field_names: Ordered metadata field names that can satisfy the
            requirement. Multiple names are supported for legacy compatibility.
        owner: Architectural layer responsible for populating the field.
        description: Human-readable reason this field matters operationally.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    field_names: tuple[str, ...] = Field(min_length=1)
    owner: str = Field(min_length=1)
    description: str = Field(min_length=1)

    @property
    def primary_field_name(self) -> str:
        """Return the canonical field name used for issue reporting."""
        return self.field_names[0]
