"""Accelerator settings for the Docling parser backend."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .docling_accelerator_device import DoclingAcceleratorDevice


class DoclingAcceleratorConfig(BaseModel):
    """Configure how Docling executes model inference."""

    model_config = ConfigDict(frozen=True)

    device: DoclingAcceleratorDevice = Field(
        default=DoclingAcceleratorDevice.AUTO,
        description="Execution device passed to Docling accelerator options.",
    )
    num_threads: int | None = Field(
        default=None,
        ge=1,
        description="Optional CPU thread limit for Docling model inference.",
    )
