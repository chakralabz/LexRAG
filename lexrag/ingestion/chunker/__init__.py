"""Public chunker package exports with lazy loading.

The chunker package now has explicit internal boundaries:

- `schemas/` holds Pydantic contracts shared across layers.
- planners/builders/factories implement the chunking workflow.
- compatibility shims preserve older import paths during migration.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "BaseChunker": (".strategies", "BaseChunker"),
    "Chunk": (".schemas", "Chunk"),
    "ChunkerFactory": (".factories", "ChunkerFactory"),
    "ChunkerKind": (".config", "ChunkerKind"),
    "ChunkMetadata": (".schemas.chunk_metadata", "ChunkMetadata"),
    "ChunkingPipeline": (".chunking_pipeline", "ChunkingPipeline"),
    "ChunkingPipelineResult": (
        ".chunking_pipeline_result",
        "ChunkingPipelineResult",
    ),
    "ChunkingConfig": (".config", "ChunkingConfig"),
    "ChunkingStrategy": (".config", "ChunkingStrategy"),
    "ChunkType": (".config", "ChunkType"),
    "Chunker": (".contracts", "Chunker"),
    "ChunkModelFactory": (".factories", "ChunkModelFactory"),
    "FixedSizeChunker": (".strategies", "FixedSizeChunker"),
    "OversizedChunkStrategy": (".config", "OversizedChunkStrategy"),
    "PlannedChunkUnit": (".schemas.planned_chunk", "PlannedChunk"),
    "RawChunkPayload": (".schemas.raw_chunk_payload", "RawChunkPayload"),
    "SemanticChunker": (".strategies", "SemanticChunker"),
    "SimilarityEngine": (".support", "SimilarityEngine"),
    "TokenContext": (".schemas.token_context", "TokenContext"),
    "TokenizationEngine": (".support", "TokenizationEngine"),
}


def _load_export(*, module_path: str, symbol: str) -> Any:
    """Import one symbol lazily from its module path."""
    module = import_module(module_path, package=__name__)
    return getattr(module, symbol)


def __getattr__(name: str) -> Any:
    """Resolve chunker exports lazily to break circular import chains."""
    export = _EXPORTS.get(name)
    if export is not None:
        module_path, symbol = export
        return _load_export(module_path=module_path, symbol=symbol)
    raise AttributeError(f"module 'lexrag.ingestion.chunker' has no attribute {name!r}")
