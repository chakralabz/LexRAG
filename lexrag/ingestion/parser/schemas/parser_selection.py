"""Schema for parser routing decisions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ParserSelection(BaseModel):
    """Describes the parser route chosen for a document."""

    model_config = ConfigDict(frozen=True)

    primary_parser_name: str = Field(description="Parser expected to run first.")
    parser_order: list[str] = Field(description="Ordered list of parser backend names.")
    fallback_chain: list[str] = Field(
        description="Fallback backends after the primary parser."
    )
    route_reason: str = Field(description="Why this parser route was chosen.")
    requires_ocr: bool = Field(description="Whether the route depends on OCR.")
    scanned_pdf: bool = Field(description="Whether the document appears scanned.")
    image_heavy: bool = Field(description="Whether the document appears image-heavy.")
    encrypted: bool = Field(description="Whether the document is encrypted.")
