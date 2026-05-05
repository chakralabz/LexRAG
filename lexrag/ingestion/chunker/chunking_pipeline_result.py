"""Structured stage output for the chunking package pipeline."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.normalized_block_pipeline_result import (
    NormalizedBlockPipelineResult,
)
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class ChunkingPipelineResult(BaseModel):
    """Capture chunking inputs, curated blocks, and final chunk outputs."""

    model_config = ConfigDict(frozen=True)

    input_blocks: list[ParsedBlock] = Field(default_factory=list)
    curated_blocks: NormalizedBlockPipelineResult = Field()
    chunks: list[Chunk] = Field(default_factory=list)
    strategy_name: str = Field()
