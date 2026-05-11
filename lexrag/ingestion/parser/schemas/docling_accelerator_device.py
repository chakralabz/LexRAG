"""Accelerator device values supported by Docling."""

from __future__ import annotations

from enum import StrEnum


class DoclingAcceleratorDevice(StrEnum):
    """Enumerate accelerator devices supported by Docling."""

    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"
    XPU = "xpu"
