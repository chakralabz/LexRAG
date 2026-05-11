"""Factories for chunker package models and strategies."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["ChunkModelFactory", "ChunkerFactory"]

_EXPORTS: dict[str, tuple[str, str]] = {
    "ChunkerFactory": (
        "lexrag.ingestion.chunker.factories.chunker_factory",
        "ChunkerFactory",
    ),
    "ChunkModelFactory": (
        "lexrag.ingestion.chunker.factories.chunk_model_factory",
        "ChunkModelFactory",
    ),
}


def __getattr__(name: str) -> Any:
    """Resolve factory exports lazily to avoid import cycles."""
    export = _EXPORTS.get(name)
    if export is None:
        raise AttributeError(
            f"module 'lexrag.ingestion.chunker.factories' has no attribute {name!r}"
        )
    module_path, symbol = export
    module = import_module(module_path)
    return getattr(module, symbol)
