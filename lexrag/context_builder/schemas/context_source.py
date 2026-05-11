"""Context-source contract consumed by prompt assembly and generation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.citation.schemas import ResolvedCitation
from lexrag.indexing.schemas import Chunk


class ContextSource(BaseModel):
    """Represents one citation-linked chunk inside the prompt context.

    Attributes:
        chunk: Canonical chunk payload returned by retrieval and reranking.
        citation: Resolved citation metadata shown to the generator.
        rank_score: Query-time ranking score used for ordering and trimming.
        quality_score: Chunk quality used when deciding what to remove first.
        token_count: Prompt token estimate for this source.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    chunk: Chunk
    citation: ResolvedCitation
    rank_score: float = Field(default=0.0)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    token_count: int = Field(ge=0)
