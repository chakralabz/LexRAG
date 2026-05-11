"""Helpers for applying metadata filters consistently across backends."""

from __future__ import annotations

from typing import Any

from lexrag.ingestion.chunker.schemas.chunk import Chunk


def matches_metadata_filters(
    *,
    chunk: Chunk,
    metadata_filters: dict[str, Any] | None,
) -> bool:
    """Return whether a chunk satisfies exact-match metadata filters.

    Args:
        chunk: Candidate chunk to evaluate.
        metadata_filters: Optional equality filters keyed by chunk metadata
            field name.

    Returns:
        `True` when all provided filters match.
    """

    if not metadata_filters:
        return True
    payload = chunk.metadata.model_dump(mode="json")
    return all(payload.get(key) == value for key, value in metadata_filters.items())
