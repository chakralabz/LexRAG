"""Schema for the full parsing outcome."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .parse_attempt import ParseAttempt
from .parsed_block import ParsedBlock
from .parser_selection import ParserSelection


class DocumentParseResult(BaseModel):
    """Structured result for one parsing request."""

    model_config = ConfigDict(frozen=True)

    blocks: list[ParsedBlock] = Field(
        description="Parsed blocks emitted by the successful backend."
    )
    attempts: list[ParseAttempt] = Field(
        description="Backend attempts executed for the document."
    )
    selection: ParserSelection = Field(
        description="Parser route selected for the document."
    )
    parser_used: str = Field(
        description="Successful parser name or terminal recovery state."
    )
    fallback_used: str | None = Field(
        default=None,
        description="Fallback parser name when a non-primary backend succeeded.",
    )
    ocr_used: str | None = Field(
        default=None, description="OCR backend name when used."
    )
    scanned_pdf: bool = Field(description="Whether the document appeared scanned.")
    encrypted: bool = Field(description="Whether the document was encrypted.")
    image_heavy: bool = Field(description="Whether the document appeared image-heavy.")
    partial_extraction: bool = Field(
        description="Whether the document was only partially extracted."
    )
    manual_recovery_required: bool = Field(
        description="Whether the document must be quarantined for manual recovery."
    )
