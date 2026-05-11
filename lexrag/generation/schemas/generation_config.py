"""Configuration schema for answer generation and validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GenerationConfig(BaseModel):
    """Tune prompt policy and validation behavior for factual RAG answers.

    Attributes:
        system_role_prompt: Stable role framing for the answer model.
        temperature: Decoding temperature used for answer generation.
        max_answer_tokens: Maximum completion length requested from the model.
        abstention_phrases: Canonical phrases treated as explicit abstentions.
    """

    model_config = ConfigDict(frozen=True)

    system_role_prompt: str = Field(
        default="You are a careful legal RAG assistant that answers only from provided sources."
    )
    temperature: float = Field(default=0.1, ge=0.0, le=0.2)
    max_answer_tokens: int = Field(default=512, ge=32, le=4096)
    abstention_phrases: tuple[str, ...] = Field(
        default=(
            "i cannot determine",
            "the provided sources do not contain",
            "i do not have enough information",
            "the answer is not in the provided sources",
        )
    )
