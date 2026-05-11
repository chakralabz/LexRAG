"""Shared helper functions for Qdrant store backends."""

from __future__ import annotations

import math
from datetime import date
from typing import Any

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.schemas.chunk_metadata import ChunkMetadata


def cosine_similarity(lhs: list[float], rhs: list[float]) -> float:
    """Computes cosine similarity between two vectors."""
    if not lhs or not rhs:
        return 0.0
    dot = sum(
        lhs_value * rhs_value for lhs_value, rhs_value in zip(lhs, rhs, strict=False)
    )
    lhs_norm = math.sqrt(sum(value * value for value in lhs))
    rhs_norm = math.sqrt(sum(value * value for value in rhs))
    if lhs_norm == 0.0 or rhs_norm == 0.0:
        return 0.0
    return dot / (lhs_norm * rhs_norm)


def matches_filters(chunk: Chunk, metadata_filters: dict[str, Any] | None) -> bool:
    """Checks whether chunk metadata matches all provided filters."""
    if not metadata_filters:
        return True
    metadata_payload = chunk.metadata.model_dump(mode="json")
    return all(
        metadata_payload.get(key) == value for key, value in metadata_filters.items()
    )


def build_chunk_payload(chunk: Chunk) -> dict[str, Any]:
    """Converts a `Chunk` into a Qdrant payload dictionary."""
    metadata = chunk.metadata.model_dump(mode="json")
    return {"chunk_id": chunk.chunk_id, "text": chunk.text, "metadata": metadata}


def chunk_from_payload(
    payload: dict[str, Any], vector: list[float] | None = None
) -> Chunk:
    """Builds a typed `Chunk` from Qdrant payload data."""
    metadata_payload = payload.get("metadata") or {}
    if isinstance(metadata_payload.get("doc_date"), str):
        try:
            metadata_payload["doc_date"] = date.fromisoformat(
                metadata_payload["doc_date"]
            )
        except ValueError:
            metadata_payload["doc_date"] = None
    metadata = ChunkMetadata.model_validate(metadata_payload)
    return Chunk(
        chunk_id=str(payload.get("chunk_id", "unknown_0")),
        text=str(payload.get("text", "")),
        metadata=metadata,
        embedding=vector,
    )
