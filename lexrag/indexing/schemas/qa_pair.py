"""Evaluation dataset contract for retrieval and generation benchmarks."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QAPair(BaseModel):
    """One evaluation question with retrieval ground truth.

    Attributes:
        question_id: Stable identifier for the evaluation record.
        question: Natural-language user question.
        gold_answer: Reference answer used by downstream generation metrics.
        gold_chunk_ids: Expected chunk identifiers that should support the
            answer.
        gold_doc_ids: Optional expected source documents for coarse recall.
        difficulty: Difficulty bucket used for ablations and slice reporting.
        notes: Optional human-authored annotation.
    """

    model_config = ConfigDict(frozen=True)

    question_id: str = Field(description="Stable evaluation question ID.")
    question: str = Field(description="User-facing evaluation question.")
    gold_answer: str = Field(description="Reference answer text.")
    gold_chunk_ids: list[str] = Field(
        description="Chunk IDs expected to support the answer."
    )
    gold_doc_ids: list[str] | None = Field(default=None)
    difficulty: Literal["factoid", "multi_hop", "unanswerable", "temporal"]
    notes: str | None = Field(default=None)
