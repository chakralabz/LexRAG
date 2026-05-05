"""Planner output schema for block-aware chunking decisions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.ingestion.chunker.config.chunking_strategy import ChunkingStrategy
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class PlannedChunk(BaseModel):
    """Represents one planner decision for a single normalized block.

    The planner's job is to annotate the input stream with intent, not to build
    chunks directly. This model captures those intent signals explicitly so the
    builder can remain deterministic and easy to reason about.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    block: ParsedBlock = Field(description="Source parsed block.")
    text: str = Field(description="Trimmed block text used by builder logic.")
    token_count: int = Field(ge=0, description="Token count for sizing decisions.")
    chunking_strategy: ChunkingStrategy = Field(
        description="Planner-selected strategy."
    )
    standalone: bool = Field(description="Whether the block must remain isolated.")
    merge_with_next: bool = Field(description="Whether adjacent merge is allowed.")
    overlap_candidate: bool = Field(description="Whether boundary overlap is useful.")
    section_boundary: bool = Field(description="Whether the block starts a new region.")
    heading_anchor: str | None = Field(
        default=None,
        description="Resolved heading context to preserve in downstream chunks.",
    )
