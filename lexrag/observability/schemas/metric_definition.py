"""Schema for a monitoring metric contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.observability.schemas.alert_threshold import AlertThreshold


class MetricDefinition(BaseModel):
    """Describe one metric exposed for dashboards, SLOs, and alerts.

    Attributes:
        name: Stable metric name used in dashboards and alert rules.
        layer: Architectural layer that owns the metric.
        description: Operational meaning of the metric.
        alert_threshold: Optional warning and critical thresholds.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    name: str = Field(min_length=1)
    layer: str = Field(min_length=1)
    description: str = Field(min_length=1)
    alert_threshold: AlertThreshold | None = Field(default=None)
