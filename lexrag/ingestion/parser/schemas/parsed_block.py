"""Canonical parsed block schema."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ParsedBlock(BaseModel):
    """Canonical parsed content block emitted by the parsing layer.

    A parsed block is the contract between parsing and normalization. The model
    intentionally carries provenance, structural, and quality metadata so later
    pipeline stages do not need to re-infer parser context.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    doc_id: str | None = Field(default=None, description="Stable source document ID.")
    source_path: str | None = Field(default=None, description="Filesystem source path.")
    source_name: str | None = Field(default=None, description="Source filename.")
    doc_type: str | None = Field(
        default=None, description="Document type or extension."
    )
    block_id: str = Field(description="Deterministic block identifier.")
    page: int = Field(ge=1, description="One-based source page number.")
    section: str = Field(description="Human-readable source section label.")
    heading_level: int | None = Field(
        default=None,
        ge=1,
        le=6,
        description="Heading depth when the block is a heading.",
    )
    block_type: str = Field(default="paragraph", description="Normalized block type.")
    text: str = Field(default="", description="Plain text extracted for the block.")
    markdown: str | None = Field(
        default=None, description="Markdown view of the block."
    )
    bbox: tuple[float, float, float, float] | None = Field(
        default=None,
        description="Optional bounding box coordinates in source page space.",
    )
    order_in_page: int | None = Field(
        default=None,
        ge=0,
        description="Stable order within the page when known.",
    )
    is_ocr: bool = Field(default=False, description="Whether OCR produced the text.")
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="OCR or parser confidence when provided by the backend.",
    )
    parent_section_path: list[str] = Field(
        default_factory=list,
        description="Section lineage used by normalization and chunking.",
    )
    parser_used: str | None = Field(default=None, description="Successful parser name.")
    fallback_used: str | None = Field(
        default=None,
        description="Fallback parser name when the primary parser failed.",
    )
    is_fallback_used: bool = Field(
        default=False,
        description="Whether a non-primary parser produced the final output.",
    )
    ocr_used: str | None = Field(default=None, description="OCR backend when used.")
    parse_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Final parse confidence attached by the orchestrator.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional parser and pipeline metadata.",
    )
