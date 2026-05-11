"""Readiness contract for the serving layer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ServiceReadiness(BaseModel):
    """Describe whether the service can safely accept production traffic."""

    model_config = ConfigDict(frozen=True)

    ready: bool
    issues: list[str] = Field(default_factory=list)
