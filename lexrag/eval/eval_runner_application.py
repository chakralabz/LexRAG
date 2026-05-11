"""Eval runner application composition."""

from __future__ import annotations

from lexrag.eval.eval_cli_config import EvalCLIConfig
from lexrag.eval.eval_dataset_repository import EvalDatasetRepository
from lexrag.eval.eval_indexer import EvalIndexer
from lexrag.eval.eval_result_writer import EvalResultWriter
from lexrag.eval.eval_store_factory import EvalStoreFactory
from lexrag.eval.retrieval_eval_runner import RetrievalEvalRunner
from lexrag.eval.retrieval_evaluator import RetrievalEvaluator
from lexrag.ingestion.chunker import Chunker, FixedSizeChunker, SemanticChunker
from lexrag.ingestion.embedder import EmbeddingMode, build_embedder
from lexrag.ingestion.parser import FallbackDocumentParser
from lexrag.observability.logging_runtime import get_logger

logger = get_logger(__name__)


class EvalRunnerApplication:
    """Composes indexer/evaluator/writer into a runnable CLI app."""

    def __init__(self, *, store_factory: EvalStoreFactory) -> None:
        self.store_factory = store_factory

    def _build_chunker(self, *, kind: str, embedding_mode: EmbeddingMode) -> Chunker:
        if kind == "fixed":
            return FixedSizeChunker()
        if kind == "semantic":
            return SemanticChunker(embedding_mode=embedding_mode)
        raise ValueError(f"Unsupported chunker kind: {kind}")

    def run(self, *, config: EvalCLIConfig) -> int:
        """Executes retrieval eval for resolved CLI config."""
        runner = self._build_runner(config)
        results, output_path = runner.run(
            dataset_path=config.dataset_path,
            input_dir=config.input_dir,
            limit_docs=config.limit_docs,
            max_questions=config.max_ci_cases if config.split == "ci" else None,
            output_dir=config.output_dir,
            output_file=config.output_file,
        )
        self._log_summary(results, split=config.split, output_path=output_path)
        return 0

    def _build_runner(self, config: EvalCLIConfig) -> RetrievalEvalRunner:
        dense_store = self.store_factory.create_dense_store(
            collection_name=config.qdrant_collection
        )
        sparse_store = None
        if config.retrieval_mode == "hybrid":
            sparse_store = self.store_factory.create_sparse_store(
                index_name=config.elasticsearch_index
            )
        indexer = EvalIndexer(
            parser=FallbackDocumentParser(),
            chunker=self._build_chunker(
                kind=config.chunker_kind,
                embedding_mode=config.embedding_mode,
            ),
            embedder=build_embedder(mode=config.embedding_mode),
            dense_store=dense_store,
            sparse_store=sparse_store,
            retrieval_mode=config.retrieval_mode,
        )
        return RetrievalEvalRunner(
            dataset_repository=EvalDatasetRepository(),
            indexer=indexer,
            evaluator=RetrievalEvaluator(),
            writer=EvalResultWriter(),
        )

    def _log_summary(
        self, results: dict[str, object], *, split: str, output_path
    ) -> None:
        summary = results["summary"]
        assert isinstance(summary, dict)
        logger.info(
            "Loaded %d QA pairs for split '%s'.", summary.get("num_questions", 0), split
        )
        logger.info(
            "MRR@5={mrr_at_5} NDCG@5={ndcg_at_5} Recall@10={recall_at_10}".format(
                **summary,
            )
        )
        logger.info("Saved eval results to %s", output_path)
