"""Docling-specific parser settings."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .docling_accelerator_config import DoclingAcceleratorConfig
from .docling_ocr_config import DoclingOcrConfig
from .docling_table_mode import DoclingTableMode


class DoclingConfig(BaseModel):
    """Configure the Docling backend for production use."""

    model_config = ConfigDict(frozen=True)

    artifacts_path: str | None = Field(
        default=None,
        description="Optional local model-artifact directory for offline or warm startup.",
    )
    document_timeout_seconds: float | None = Field(
        default=None,
        gt=0.0,
        description="Optional per-document timeout enforced by Docling.",
    )
    enable_remote_services: bool = Field(
        default=False,
        description="Whether Docling may call remote model services.",
    )
    allow_external_plugins: bool = Field(
        default=False,
        description="Whether Docling may load third-party plugins.",
    )
    do_ocr: bool = Field(
        default=True,
        description="Whether Docling OCR should be enabled for PDF parsing.",
    )
    do_table_structure: bool = Field(
        default=True,
        description="Whether Docling should run table structure extraction.",
    )
    do_code_enrichment: bool = Field(
        default=False,
        description="Whether Docling code enrichment should run.",
    )
    do_formula_enrichment: bool = Field(
        default=False,
        description="Whether Docling formula enrichment should run.",
    )
    force_backend_text: bool = Field(
        default=False,
        description="Whether backend text should be forced instead of model-derived text.",
    )
    generate_page_images: bool = Field(
        default=False,
        description="Whether Docling should retain rendered page images.",
    )
    generate_parsed_pages: bool = Field(
        default=False,
        description="Whether Docling should keep parsed page objects in the result.",
    )
    generate_table_images: bool = Field(
        default=False,
        description="Whether Docling should retain table crops in the result.",
    )
    images_scale: float | None = Field(
        default=None,
        gt=0.0,
        description="Optional image scale override used by Docling rendering stages.",
    )
    ocr_batch_size: int | None = Field(
        default=None,
        ge=1,
        description="Optional OCR stage batch size.",
    )
    layout_batch_size: int | None = Field(
        default=None,
        ge=1,
        description="Optional layout stage batch size.",
    )
    table_batch_size: int | None = Field(
        default=None,
        ge=1,
        description="Optional table stage batch size.",
    )
    batch_polling_interval_seconds: float | None = Field(
        default=None,
        gt=0.0,
        description="Optional polling interval for the threaded PDF pipeline.",
    )
    queue_max_size: int | None = Field(
        default=None,
        ge=1,
        description="Optional inter-stage queue size for the threaded PDF pipeline.",
    )
    table_cell_matching: bool = Field(
        default=True,
        description="Whether Docling should map predicted table structure back to PDF cells.",
    )
    table_mode: DoclingTableMode | None = Field(
        default=None,
        description="Optional TableFormer mode such as 'accurate' or 'fast'.",
    )
    require_local_artifacts: bool = Field(
        default=False,
        description="Fail startup if Docling artifacts_path is configured but missing.",
    )
    preload_artifacts: bool = Field(
        default=False,
        description="Whether parser warmup should prefetch Docling models before first use.",
    )
    accelerator: DoclingAcceleratorConfig = Field(
        default_factory=DoclingAcceleratorConfig,
        description="Accelerator settings used by Docling models.",
    )
    ocr: DoclingOcrConfig = Field(
        default_factory=DoclingOcrConfig,
        description="OCR engine settings used by Docling.",
    )
