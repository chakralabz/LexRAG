"""Resolved configuration model for eval CLI runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lexrag.eval.retrieval_mode import RetrievalMode
from lexrag.ingestion.embedder import EmbeddingMode


@dataclass(frozen=True, slots=True)
class EvalCLIConfig:
    """Resolved runtime configuration for eval CLI execution."""

    split: str
    dataset_path: Path
    input_dir: Path
    limit_docs: int | None
    max_ci_cases: int | None
    output_dir: Path
    output_file: str
    chunker_kind: str
    embedding_mode: EmbeddingMode
    retrieval_mode: RetrievalMode
    qdrant_collection: str
    elasticsearch_index: str
