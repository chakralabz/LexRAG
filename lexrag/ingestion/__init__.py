"""Lightweight ingestion package exports.

This module intentionally avoids eager imports so parser-only paths do not
require chunking/tokenizer dependencies at import time.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "BGEEmbedder",
    "BlockDeduplicator",
    "BlockQualityValidator",
    "Chunker",
    "Deduplicator",
    "EmbeddingMode",
    "FallbackDocumentParser",
    "FixedSizeChunker",
    "IngestPipeline",
    "IngestionDocumentResult",
    "IngestionSummary",
    "MinHashDeduplicator",
    "SemanticChunker",
    "build_embedder",
]


def _chunker_exports() -> dict[str, Any]:
    """Resolve chunker-facing public exports lazily."""
    from lexrag.ingestion.chunker import Chunker, FixedSizeChunker, SemanticChunker

    return {
        "Chunker": Chunker,
        "FixedSizeChunker": FixedSizeChunker,
        "SemanticChunker": SemanticChunker,
    }


def _deduplicator_exports() -> dict[str, Any]:
    """Resolve deduplicator-facing public exports lazily."""
    from lexrag.ingestion.deduplicator import (
        BlockDeduplicator,
        Deduplicator,
        MinHashDeduplicator,
    )

    return {
        "BlockDeduplicator": BlockDeduplicator,
        "Deduplicator": Deduplicator,
        "MinHashDeduplicator": MinHashDeduplicator,
    }


def _embedder_exports() -> dict[str, Any]:
    """Resolve embedding-facing public exports lazily."""
    from lexrag.ingestion.embeddings import BGEEmbedder, EmbeddingMode, build_embedder

    return {
        "BGEEmbedder": BGEEmbedder,
        "EmbeddingMode": EmbeddingMode,
        "build_embedder": build_embedder,
    }


def __getattr__(name: str) -> Any:
    """Resolve ingestion exports lazily to avoid hard dependency coupling."""
    if name in {"Chunker", "FixedSizeChunker", "SemanticChunker"}:
        return _chunker_exports()[name]
    if name in {
        "BlockDeduplicator",
        "Deduplicator",
        "MinHashDeduplicator",
    }:
        return _deduplicator_exports()[name]
    if name == "BlockQualityValidator":
        from lexrag.ingestion.block_quality import BlockQualityValidator

        return BlockQualityValidator
    if name in {"BGEEmbedder", "EmbeddingMode", "build_embedder"}:
        return _embedder_exports()[name]
    if name == "FallbackDocumentParser":
        from lexrag.ingestion.parser import FallbackDocumentParser

        return FallbackDocumentParser
    if name == "IngestionDocumentResult":
        from lexrag.ingestion.ingestion_document_result import IngestionDocumentResult

        return IngestionDocumentResult
    if name == "IngestionSummary":
        from lexrag.ingestion.ingestion_summary import IngestionSummary

        return IngestionSummary
    if name == "IngestPipeline":
        from lexrag.ingestion.pipeline import IngestPipeline

        return IngestPipeline
    raise AttributeError(f"module 'lexrag.ingestion' has no attribute {name!r}")
