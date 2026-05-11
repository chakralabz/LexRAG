"""Serialize and deserialize dense-store payloads."""

from __future__ import annotations

from datetime import UTC, datetime

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.schemas.chunk_metadata import ChunkMetadata


def build_payload(*, chunk: Chunk) -> dict[str, object]:
    """Build a Qdrant-safe payload from a canonical chunk.

    Args:
        chunk: Chunk to serialize.

    Returns:
        Payload containing retrieval-safe text plus filterable metadata.
    """

    metadata = chunk.metadata.model_dump(mode="json")
    return {
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "embedding_text": chunk.embedding_text,
        "doc_id": metadata.get("doc_id"),
        "document_version": metadata.get("document_version"),
        "doc_type": metadata.get("doc_type"),
        "section_path": metadata.get("section_path"),
        "page_start": metadata.get("page_start"),
        "chunk_type": metadata.get("chunk_type"),
        "parser_used": metadata.get("parser_used"),
        "parse_confidence": metadata.get("parse_confidence"),
        "chunk_quality_score": metadata.get("chunk_quality_score"),
        "ingestion_timestamp": datetime.now(UTC).isoformat(),
        "metadata": metadata,
    }


def chunk_from_payload(
    *,
    payload: dict[str, object],
    vector: list[float] | None,
) -> Chunk:
    """Rehydrate a canonical chunk from a stored payload.

    Args:
        payload: Raw backend payload.
        vector: Optional stored embedding vector.

    Returns:
        Canonical chunk instance.
    """

    metadata = ChunkMetadata.model_validate(payload.get("metadata") or {})
    return Chunk(
        chunk_id=str(payload.get("chunk_id", "unknown_chunk")),
        text=str(payload.get("text", "")),
        embedding_text=_optional_text(value=payload.get("embedding_text")),
        metadata=metadata,
        embedding=vector,
    )


def _optional_text(*, value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None
