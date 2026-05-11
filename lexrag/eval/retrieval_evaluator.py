"""Retrieval metric evaluator."""

from __future__ import annotations

from tqdm import tqdm

from lexrag.eval.eval_score_config import EvalScoreConfig
from lexrag.eval.indexed_corpus import IndexedCorpus
from lexrag.indexing.schemas import QAPair
from lexrag.metrics.metrics import (
    citation_auditability_score,
    low_auditability_chunk_ids,
    mrr_at_k,
    ndcg_at_k,
    recall_at_k,
)


class RetrievalEvaluator:
    """Computes per-question and aggregate retrieval metrics."""

    def __init__(self, *, config: EvalScoreConfig | None = None) -> None:
        self.config = config or EvalScoreConfig()

    def evaluate(
        self, *, qa_pairs: list[QAPair], indexed: IndexedCorpus
    ) -> dict[str, object]:
        """Runs retrieval evaluation and returns result payload."""
        all_chunk_ids = {chunk.chunk_id for chunk in indexed.chunks}
        per_question: list[dict[str, object]] = []
        totals = {"mrr": 0.0, "ndcg": 0.0, "recall": 0.0}
        for pair in tqdm(qa_pairs, desc="Evaluating questions", unit="q"):
            row, scores = self._evaluate_pair(
                pair=pair,
                indexed=indexed,
                all_chunk_ids=all_chunk_ids,
            )
            per_question.append(row)
            totals["mrr"] += scores[0]
            totals["ndcg"] += scores[1]
            totals["recall"] += scores[2]
        return {
            "summary": self._build_summary(qa_pairs, indexed, totals),
            "per_question": per_question,
        }

    def _evaluate_pair(
        self,
        *,
        pair: QAPair,
        indexed: IndexedCorpus,
        all_chunk_ids: set[str],
    ) -> tuple[dict[str, object], tuple[float, float, float]]:
        retrieved = indexed.retriever.retrieve(
            pair.question, top_k=self.config.retriever_top_k
        )
        retrieved_ids = [chunk.chunk_id for chunk in retrieved]
        gold_ids = self._resolve_gold_ids(pair, indexed.chunk_ids_by_doc)
        gold_ids = [chunk_id for chunk_id in gold_ids if chunk_id in all_chunk_ids]
        mrr_score = mrr_at_k(retrieved_ids, gold_ids, k=self.config.mrr_k)
        ndcg_score = ndcg_at_k(retrieved_ids, gold_ids, k=self.config.ndcg_k)
        recall_score = recall_at_k(retrieved_ids, gold_ids, k=self.config.recall_k)
        row = {
            "question_id": pair.question_id,
            "difficulty": pair.difficulty,
            "retrieved_ids": retrieved_ids,
            "gold_chunk_ids": gold_ids,
            "gold_doc_ids": pair.gold_doc_ids or [],
            "mrr_at_5": round(mrr_score, 6),
            "ndcg_at_5": round(ndcg_score, 6),
            "recall_at_10": round(recall_score, 6),
        }
        return row, (mrr_score, ndcg_score, recall_score)

    def _resolve_gold_ids(
        self, pair: QAPair, chunk_ids_by_doc: dict[str, list[str]]
    ) -> list[str]:
        gold_ids: list[str] = []
        if pair.gold_doc_ids:
            for doc_id in pair.gold_doc_ids:
                gold_ids.extend(chunk_ids_by_doc.get(doc_id, []))
        if pair.gold_chunk_ids:
            gold_ids.extend(pair.gold_chunk_ids)
        return list(dict.fromkeys(gold_ids))

    def _build_summary(
        self,
        qa_pairs: list[QAPair],
        indexed: IndexedCorpus,
        totals: dict[str, float],
    ) -> dict[str, object]:
        denom = max(len(qa_pairs), 1)
        return {
            "num_questions": len(qa_pairs),
            "num_docs_ingested": indexed.num_docs_ingested,
            "num_chunks_indexed": len(indexed.chunks),
            "mrr_at_5": round(totals["mrr"] / denom, 6),
            "ndcg_at_5": round(totals["ndcg"] / denom, 6),
            "recall_at_10": round(totals["recall"] / denom, 6),
            "citation_auditability": round(
                citation_auditability_score(indexed.chunks), 6
            ),
            "low_auditability_chunks": len(low_auditability_chunk_ids(indexed.chunks)),
            "fallback_reason_counts": indexed.fallback_reason_counts,
            "parse_failure_counts": indexed.parse_failure_counts,
        }
