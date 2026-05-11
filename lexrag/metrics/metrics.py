"""Evaluation metrics for retrieval quality and citation auditability."""

from __future__ import annotations

import math

from lexrag.indexing.schemas import Chunk


def mrr_at_k(retrieved_ids: list[str], gold_ids: list[str], *, k: int) -> float:
    """Compute mean reciprocal rank for one query at cutoff ``k``."""
    if k <= 0 or not gold_ids:
        return 0.0
    gold = set(gold_ids)
    for rank, chunk_id in enumerate(retrieved_ids[:k], start=1):
        if chunk_id in gold:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved_ids: list[str], gold_ids: list[str], *, k: int) -> float:
    """Compute normalized discounted cumulative gain at cutoff ``k``."""
    if k <= 0 or not gold_ids:
        return 0.0
    gold = set(gold_ids)
    dcg = 0.0
    for rank, chunk_id in enumerate(retrieved_ids[:k], start=1):
        if chunk_id in gold:
            dcg += 1.0 / math.log2(rank + 1)
    ideal_hits = min(len(gold), k)
    ideal_dcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    if ideal_dcg == 0.0:
        return 0.0
    return dcg / ideal_dcg


def recall_at_k(retrieved_ids: list[str], gold_ids: list[str], *, k: int) -> float:
    """Compute recall at cutoff ``k`` for one query."""
    if k <= 0 or not gold_ids:
        return 0.0
    gold = set(gold_ids)
    hits = gold.intersection(retrieved_ids[:k])
    return len(hits) / len(gold)


def faithfulness_score(answer: str, citations: list[object]) -> float:
    """Return a placeholder generation faithfulness score."""
    _ = answer, citations
    return 0.0


def bertscore_f1(generated: str, gold: str) -> float:
    """Return a placeholder BERTScore F1 value."""
    _ = generated, gold
    return 0.0


def citation_accuracy(predicted: list[object], expected: list[object]) -> float:
    """Return a placeholder citation accuracy score."""
    _ = predicted, expected
    return 0.0


def citation_auditability_score(chunks: list[Chunk]) -> float:
    """Measure the share of chunks that preserve source-span provenance."""
    if not chunks:
        return 0.0
    audited = 0
    for chunk in chunks:
        spans = chunk.metadata.metadata.get("source_spans")
        if isinstance(spans, list) and spans:
            audited += 1
    return audited / len(chunks)


def low_auditability_chunk_ids(chunks: list[Chunk]) -> list[str]:
    """Return chunk IDs that lack source-span provenance."""
    low_auditability: list[str] = []
    for chunk in chunks:
        spans = chunk.metadata.metadata.get("source_spans")
        if not isinstance(spans, list) or not spans:
            low_auditability.append(chunk.chunk_id)
    return low_auditability
