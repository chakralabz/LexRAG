"""Docling runtime validation and warmup helpers.

This module isolates the "production readiness" concerns around Docling:
artifact-path validation, optional model prefetching, and explicit pipeline
warmup.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from lexrag.ingestion.parser.schemas.docling_config import DoclingConfig


class DoclingRuntime:
    """Encapsulate Docling-specific startup checks and warmup behavior."""

    def __init__(self, *, config: DoclingConfig) -> None:
        self.config = config

    def preload(self, *, converter: Any) -> None:
        """Warm configured Docling resources before the first parse request."""
        self._validate_artifacts_path()
        self._prefetch_artifacts_if_requested()
        self._initialize_pdf_pipeline(converter=converter)

    def _validate_artifacts_path(self) -> None:
        """Validate the configured local artifacts path when required."""
        if self.config.artifacts_path is None:
            return
        artifacts_path = Path(self.config.artifacts_path)
        if artifacts_path.exists():
            return
        if self.config.require_local_artifacts:
            raise RuntimeError(
                "Configured Docling artifacts_path does not exist: "
                f"{self.config.artifacts_path}"
            )

    def _prefetch_artifacts_if_requested(self) -> None:
        """Download Docling models ahead of time when warm prefetch is enabled."""
        if not self.config.preload_artifacts:
            return
        download_models = self._load_model_downloader()
        kwargs = self._download_kwargs(download_models=download_models)
        download_models(**kwargs)

    def _load_model_downloader(self):
        """Import Docling's model downloader only when prefetch is requested."""
        try:
            from docling.utils.model_downloader import download_models
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Docling model prefetch requested, but model_downloader is unavailable."
            ) from exc
        return download_models

    def _download_kwargs(self, *, download_models: Any) -> dict[str, Any]:
        """Adapt to different Docling downloader signatures across versions."""
        signature = inspect.signature(download_models)
        if self.config.artifacts_path is None:
            return {}
        if "output_dir" in signature.parameters:
            return {"output_dir": Path(self.config.artifacts_path)}
        if "artifacts_path" in signature.parameters:
            return {"artifacts_path": Path(self.config.artifacts_path)}
        return {}

    def _initialize_pdf_pipeline(self, *, converter: Any) -> None:
        """Eagerly initialize the PDF pipeline when the converter supports it."""
        initialized = getattr(converter, "initialized_pipelines", None)
        if isinstance(initialized, dict) and initialized:
            return
        # Some Docling versions expose an explicit pipeline init hook while
        # others initialize lazily on first convert(). We support both cases.
        initialize = getattr(converter, "initialize_pipeline", None)
        if not callable(initialize):
            return
        try:
            from docling.datamodel.base_models import InputFormat
        except Exception:  # pragma: no cover
            return
        initialize(InputFormat.PDF)
