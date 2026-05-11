"""High-level retrieval eval workflow orchestrator."""

from __future__ import annotations

from pathlib import Path

from lexrag.eval.eval_dataset_repository import EvalDatasetRepository
from lexrag.eval.eval_indexer import EvalIndexer
from lexrag.eval.eval_result_writer import EvalResultWriter
from lexrag.eval.retrieval_evaluator import RetrievalEvaluator


class RetrievalEvalRunner:
    """High-level orchestrator for retrieval-eval workflows."""

    def __init__(
        self,
        *,
        dataset_repository: EvalDatasetRepository,
        indexer: EvalIndexer,
        evaluator: RetrievalEvaluator,
        writer: EvalResultWriter,
    ) -> None:
        self.dataset_repository = dataset_repository
        self.indexer = indexer
        self.evaluator = evaluator
        self.writer = writer

    def run(
        self,
        *,
        dataset_path: Path,
        input_dir: Path,
        limit_docs: int | None,
        max_questions: int | None,
        output_dir: Path,
        output_file: str,
    ) -> tuple[dict[str, object], Path]:
        qa_pairs = self.dataset_repository.load(dataset_path)
        if max_questions is not None:
            qa_pairs = qa_pairs[: min(max_questions, len(qa_pairs))]
        indexed = self.indexer.build(input_dir=input_dir, limit_docs=limit_docs)
        results = self.evaluator.evaluate(qa_pairs=qa_pairs, indexed=indexed)
        output_path = self.writer.write(
            results=results,
            output_dir=output_dir,
            output_file=output_file,
        )
        return results, output_path
