"""HTTP response contract for RAG queries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.generation.schemas import GenerationValidation


class QueryResponse(BaseModel):
    """Return the answer plus audit-friendly retrieval metadata."""

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1)
    answer_text: str = Field(default="")
    validation: GenerationValidation
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    context_warnings: list[str] = Field(default_factory=list)
