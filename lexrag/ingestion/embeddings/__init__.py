"""Unified embedding package for preparation, loading, and generation."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "BGEEmbedder",
    "DeterministicHashEmbeddingBackend",
    "EmbeddingBackend",
    "EmbeddingCache",
    "EmbeddingGenerationConfig",
    "EmbeddingGenerator",
    "EmbeddingMode",
    "EmbeddingModelPreloader",
    "EmbeddingPreparationConfig",
    "EmbeddingPreparationService",
    "EmbeddingTextBuilder",
    "SentenceTransformerEmbeddingBackend",
    "SharedModelRegistry",
    "TableEmbeddingSerializer",
    "build_embedder",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "BGEEmbedder": (".embedding_generator", "EmbeddingGenerator"),
    "DeterministicHashEmbeddingBackend": (
        ".deterministic_hash_embedding_backend",
        "DeterministicHashEmbeddingBackend",
    ),
    "EmbeddingBackend": (".embedding_backend", "EmbeddingBackend"),
    "EmbeddingCache": (".embedding_cache", "EmbeddingCache"),
    "EmbeddingGenerationConfig": (
        ".schemas.embedding_generation_config",
        "EmbeddingGenerationConfig",
    ),
    "EmbeddingGenerator": (".embedding_generator", "EmbeddingGenerator"),
    "EmbeddingMode": (".embedding_mode", "EmbeddingMode"),
    "EmbeddingModelPreloader": (
        ".embedding_model_preloader",
        "EmbeddingModelPreloader",
    ),
    "EmbeddingPreparationConfig": (
        ".schemas.embedding_preparation_config",
        "EmbeddingPreparationConfig",
    ),
    "EmbeddingPreparationService": (
        ".embedding_preparation_service",
        "EmbeddingPreparationService",
    ),
    "EmbeddingTextBuilder": (".embedding_text_builder", "EmbeddingTextBuilder"),
    "SentenceTransformerEmbeddingBackend": (
        ".sentence_transformer_embedding_backend",
        "SentenceTransformerEmbeddingBackend",
    ),
    "SharedModelRegistry": (".shared_model_registry", "SharedModelRegistry"),
    "TableEmbeddingSerializer": (
        ".table_embedding_serializer",
        "TableEmbeddingSerializer",
    ),
    "build_embedder": (".build_embedder", "build_embedder"),
}


def __getattr__(name: str) -> Any:
    """Resolve exports lazily to avoid import cycles across ingestion layers."""
    export = _EXPORTS.get(name)
    if export is None:
        raise AttributeError(
            f"module 'lexrag.ingestion.embeddings' has no attribute {name!r}"
        )
    module_path, symbol = export
    module = import_module(module_path, package=__name__)
    return getattr(module, symbol)
