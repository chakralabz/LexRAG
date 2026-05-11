"""Liveness response payload for the serving layer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.serving.schemas.service_readiness import ServiceReadiness


class HealthResponse(BaseModel):
    """Expose high-signal liveness and readiness state to operators."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(min_length=1)
    service: str = Field(min_length=1)
    readiness: ServiceReadiness
