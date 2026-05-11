"""CLI entrypoints for offline and stack retrieval evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

from lexrag.config import get_settings
from lexrag.eval.eval_cli_config import EvalCLIConfig
from lexrag.eval.eval_runner_application import EvalRunnerApplication
from lexrag.eval.offline_eval_store_factory import OfflineEvalStoreFactory
from lexrag.eval.retrieval_mode import RetrievalMode
from lexrag.eval.stack_eval_store_factory import StackEvalStoreFactory
from lexrag.ingestion.embedder import EmbeddingMode
from lexrag.utils.cli import add_optional_limit_args, resolve_optional_limit


def _build_common_parser(*, description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--split", default="ci", choices=["ci", "full"])
    parser.add_argument("--output", default=None)
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--output-file", default=None)
    parser.add_argument("--input-dir", default="data/arxiv/raw/pdf")
    add_optional_limit_args(
        parser,
        arg_name="limit-docs",
        default=25,
        help_text="Maximum documents to ingest for evaluation.",
        no_limit_help_text="Ingest all supported files from --input-dir.",
        no_limit_flag_name="no-limit-docs",
    )
    add_optional_limit_args(
        parser,
        arg_name="max-ci-cases",
        default=25,
        help_text="Maximum CI testcase rows to evaluate for split=ci.",
        no_limit_help_text="Evaluate all available CI testcase rows for split=ci.",
    )
    parser.add_argument("--chunker", choices=["fixed", "semantic"], default="semantic")
    parser.add_argument(
        "--embedding-mode",
        choices=["production", "deterministic-test-only"],
        default="production",
        help="Embedding mode for chunking and dense retrieval embedding.",
    )
    parser.add_argument(
        "--retrieval-mode",
        choices=["dense", "hybrid"],
        default="dense",
        help="Retrieval mode used during eval scoring.",
    )
    parser.add_argument("--qdrant-collection", default="eval_real")
    parser.add_argument("--elasticsearch-index", default="eval_real_bm25")
    return parser


def _resolve_dataset_and_output(
    split: str, args: argparse.Namespace
) -> tuple[Path, Path, str]:
    settings = get_settings()
    dataset_path = Path(
        args.dataset
        if args.dataset
        else (
            settings.TESTCASE_DATASET_PATH
            if split == "ci"
            else settings.EVAL_DATASET_PATH
        )
    )
    output_dir = Path(
        args.output
        if args.output
        else (
            settings.TESTCASE_RESULTS_DIR
            if split == "ci"
            else settings.EVAL_RESULTS_DIR
        )
    )
    output_file = str(
        args.output_file
        if args.output_file
        else ("phase1_baseline.json" if split == "full" else "ci_testcase_eval.json")
    )
    return dataset_path, output_dir, output_file


def _resolve_config(args: argparse.Namespace) -> EvalCLIConfig:
    split = str(args.split)
    dataset_path, output_dir, output_file = _resolve_dataset_and_output(split, args)
    return EvalCLIConfig(
        split=split,
        dataset_path=dataset_path,
        input_dir=Path(args.input_dir),
        limit_docs=resolve_optional_limit(
            args,
            limit_dest="limit_docs",
            no_limit_dest="no_limit_docs",
        ),
        max_ci_cases=resolve_optional_limit(
            args,
            limit_dest="max_ci_cases",
            no_limit_dest="no_max_ci_cases_limit",
        ),
        output_dir=output_dir,
        output_file=output_file,
        chunker_kind=str(args.chunker),
        embedding_mode=_resolve_embedding_mode(args.embedding_mode),
        retrieval_mode=_resolve_retrieval_mode(args.retrieval_mode),
        qdrant_collection=str(args.qdrant_collection),
        elasticsearch_index=str(args.elasticsearch_index),
    )


def _resolve_embedding_mode(value: str) -> EmbeddingMode:
    return value  # type: ignore[return-value]


def _resolve_retrieval_mode(value: str) -> RetrievalMode:
    return value  # type: ignore[return-value]


def run_offline_cli(argv: list[str] | None = None) -> int:
    """Runs offline eval CLI with in-memory dense/sparse stores."""
    parser = _build_common_parser(description="Run LexRAG offline retrieval eval")
    config = _resolve_config(parser.parse_args(argv))
    app = EvalRunnerApplication(store_factory=OfflineEvalStoreFactory())
    return app.run(config=config)


def run_stack_cli(argv: list[str] | None = None) -> int:
    """Runs stack eval CLI against external Qdrant/Elasticsearch services."""
    parser = _build_common_parser(
        description="Run LexRAG production-like retrieval eval (requires services)"
    )
    config = _resolve_config(parser.parse_args(argv))
    app = EvalRunnerApplication(store_factory=StackEvalStoreFactory())
    try:
        return app.run(config=config)
    except Exception as exc:
        raise RuntimeError(
            "Stack eval failed. Ensure Qdrant and Elasticsearch services are up "
            "(for example via docker compose) and models are available."
        ) from exc
