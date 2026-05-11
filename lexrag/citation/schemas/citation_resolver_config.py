"""Configuration for the citation resolver."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CitationResolverConfig(BaseModel):
    """Control deterministic citation ID assignment and input validation.

    Attributes:
        starting_citation_id: First numeric identifier exposed to generation.
        require_unique_chunk_ids: When true, duplicate chunks are rejected
            rather than silently receiving multiple citation IDs.
    """

    model_config = ConfigDict(frozen=True)

    starting_citation_id: int = Field(default=1, ge=1, le=10_000)
    require_unique_chunk_ids: bool = Field(default=True)
