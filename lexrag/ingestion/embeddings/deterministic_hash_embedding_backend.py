"""Deterministic embedding backend used for tests and local smoke checks."""

from __future__ import annotations

from hashlib import blake2b

from lexrag.ingestion.embeddings.embedding_backend import EmbeddingBackend
from lexrag.ingestion.embeddings.vector_normalizer import normalize


class DeterministicHashEmbeddingBackend(EmbeddingBackend):
    """Dependency-free backend with stable vectors for tests and CI."""

    def __init__(self, *, dimension: int = 1024) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be > 0")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        """Return the configured test vector dimension."""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Return the stable backend identifier."""
        return "deterministic-hash"

    @property
    def model_version(self) -> str:
        """Return the pseudo-version for deterministic test vectors."""
        return "v1"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate deterministic normalized vectors from token hashes."""
        return [self._vector(text=text) for text in texts]

    def _vector(self, *, text: str) -> list[float]:
        """Build one deterministic vector from a text payload."""
        vector = [0.0] * self._dimension
        for token in text.lower().split():
            digest = blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        return normalize(vector)
