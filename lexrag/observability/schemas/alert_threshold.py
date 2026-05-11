"""Schema for warning and critical alert thresholds."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AlertThreshold(BaseModel):
    """Represent warning and critical thresholds for one metric.

    Attributes:
        warning: Lower-severity alert threshold in normalized ratio units.
        critical: Higher-severity alert threshold in normalized ratio units.
        direction: Whether alerting fires when the metric goes above or below
            the configured thresholds.
    """

    model_config = ConfigDict(frozen=True)

    warning: float = Field(ge=0.0)
    critical: float = Field(ge=0.0)
    direction: Literal["above", "below"] = Field(default="above")

    @model_validator(mode="after")
    def validate_ordering(self) -> AlertThreshold:
        """Ensure threshold ordering matches the configured direction."""
        if self.direction == "above" and self.warning > self.critical:
            raise ValueError("warning threshold must be <= critical for `above`")
        if self.direction == "below" and self.warning < self.critical:
            raise ValueError("warning threshold must be >= critical for `below`")
        return self
