"""Serialize and deserialize sparse-store documents."""

from __future__ import annotations

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.schemas.chunk_metadata import ChunkMetadata


def build_document(*, chunk: Chunk) -> dict[str, object]:
    """Build a sparse-index document from a canonical chunk.

    Args:
        chunk: Chunk to serialize.

    Returns:
        Elasticsearch-safe source document.
    """

    return {
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "embedding_text": chunk.embedding_text,
        "metadata": chunk.metadata.model_dump(mode="json"),
    }


def chunk_from_document(*, source: dict[str, object]) -> Chunk:
    """Rehydrate a canonical chunk from sparse index source data.

    Args:
        source: Stored sparse document source.

    Returns:
        Canonical chunk instance.
    """

    metadata = ChunkMetadata.model_validate(source.get("metadata") or {})
    embedding_text = source.get("embedding_text")
    return Chunk(
        chunk_id=str(source.get("chunk_id", "unknown_chunk")),
        text=str(source.get("text", "")),
        embedding_text=str(embedding_text) if embedding_text else None,
        metadata=metadata,
        embedding=None,
    )
