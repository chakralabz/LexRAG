"""HTTP request contract for RAG queries."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    """Capture a user question plus optional retrieval controls."""

    model_config = ConfigDict(frozen=True)

    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    metadata_filters: dict[str, Any] | None = None
