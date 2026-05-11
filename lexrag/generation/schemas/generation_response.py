"""Response contract for answer generation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.generation.schemas.generation_validation import GenerationValidation


class GenerationResponse(BaseModel):
    """Store generated answer text plus the associated validation result."""

    model_config = ConfigDict(frozen=True)

    answer_text: str = Field(default="")
    validation: GenerationValidation
