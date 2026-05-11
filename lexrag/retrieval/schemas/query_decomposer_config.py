"""Configuration schema for heuristic query decomposition."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class QueryDecomposerConfig(BaseModel):
    """Tune deterministic query-decomposition heuristics.

    Attributes:
        max_sub_queries: Maximum number of sub-queries emitted for one question.
        min_terms_for_multihop: Minimum token count required before conjunctions
            are treated as likely multi-hop signals.
    """

    model_config = ConfigDict(frozen=True)

    max_sub_queries: int = Field(default=3, ge=2, le=6)
    min_terms_for_multihop: int = Field(default=6, ge=2, le=20)
