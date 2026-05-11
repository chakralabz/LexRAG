"""Shared helper functions for BM25 store backends."""

from __future__ import annotations

from datetime import date
from typing import Any

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.schemas.chunk_metadata import ChunkMetadata


def matches_filters(chunk: Chunk, metadata_filters: dict[str, Any] | None) -> bool:
    """Checks whether a chunk satisfies metadata equality filters."""
    if not metadata_filters:
        return True
    payload = chunk.metadata.model_dump(mode="json")
    return all(payload.get(key) == value for key, value in metadata_filters.items())


def build_doc(chunk: Chunk) -> dict[str, Any]:
    """Builds an Elasticsearch document from a chunk."""
    return {
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "metadata": chunk.metadata.model_dump(mode="json"),
    }


def chunk_from_doc(
    source: dict[str, Any], embedding: list[float] | None = None
) -> Chunk:
    """Builds typed `Chunk` from Elasticsearch `_source` payload."""
    metadata_payload = dict(source.get("metadata") or {})
    if isinstance(metadata_payload.get("doc_date"), str):
        try:
            metadata_payload["doc_date"] = date.fromisoformat(
                metadata_payload["doc_date"]
            )
        except ValueError:
            metadata_payload["doc_date"] = None
    metadata = ChunkMetadata.model_validate(metadata_payload)
    return Chunk(
        chunk_id=str(source.get("chunk_id", "unknown_0")),
        text=str(source.get("text", "")),
        metadata=metadata,
        embedding=embedding,
    )
