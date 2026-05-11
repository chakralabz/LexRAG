"""Request contract for answer generation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.context_builder.schemas import ContextWindow


class GenerationRequest(BaseModel):
    """Capture the user question and curated context required for generation."""

    model_config = ConfigDict(frozen=True)

    question: str = Field(min_length=1)
    context_window: ContextWindow
