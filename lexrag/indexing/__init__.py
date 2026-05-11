"""Public exports for the indexing layer.

The package is organized around three concerns:

- `schemas/` defines contracts owned by indexing and evaluation.
- `backends/` contains storage adapters with no orchestration policy.
- facades such as `QdrantStore` and `BM25Store` enforce architecture-level
  invariants such as version-aware upserts and filterable metadata.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "BM25Store",
    "Chunk",
    "ChunkMetadata",
    "DenseIndexConfig",
    "IndexOptimizationConfig",
    "IndexOptimizationReport",
    "QAPair",
    "QdrantStore",
    "SparseIndexConfig",
    "VectorUpsertReport",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "BM25Store": (".bm25_store", "BM25Store"),
    "Chunk": (".schemas", "Chunk"),
    "ChunkMetadata": (".schemas", "ChunkMetadata"),
    "DenseIndexConfig": (".schemas", "DenseIndexConfig"),
    "IndexOptimizationConfig": (
        ".schemas.index_optimization_config",
        "IndexOptimizationConfig",
    ),
    "IndexOptimizationReport": (
        ".schemas.index_optimization_report",
        "IndexOptimizationReport",
    ),
    "QAPair": (".schemas", "QAPair"),
    "QdrantStore": ("lexrag.vector.qdrant_store", "QdrantStore"),
    "SparseIndexConfig": (".schemas.sparse_index_config", "SparseIndexConfig"),
    "VectorUpsertReport": (".schemas", "VectorUpsertReport"),
}


def __getattr__(name: str) -> Any:
    """Resolve exports lazily to keep package boundaries import-safe."""

    export = _EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module 'lexrag.indexing' has no attribute {name!r}")
    module_path, symbol = export
    module = import_module(module_path, package=__name__)
    return getattr(module, symbol)
