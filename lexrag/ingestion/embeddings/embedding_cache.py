"""In-memory cache for duplicate embedding requests."""

from __future__ import annotations


class EmbeddingCache:
    """Cache embeddings for identical embedding text."""

    def __init__(self) -> None:
        self._vectors: dict[str, list[float]] = {}

    def get(self, *, text: str) -> list[float] | None:
        """Return a cached vector when present."""
        vector = self._vectors.get(text)
        if vector is None:
            return None
        return list(vector)

    def set(self, *, text: str, vector: list[float]) -> None:
        """Store a normalized vector in the cache."""
        self._vectors[text] = list(vector)
