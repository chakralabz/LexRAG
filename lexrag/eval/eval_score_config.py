"""Eval metric cutoff configuration model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvalScoreConfig:
    """Metric cutoffs for retrieval evaluation."""

    mrr_k: int = 5
    ndcg_k: int = 5
    recall_k: int = 10
    retriever_top_k: int = 10
