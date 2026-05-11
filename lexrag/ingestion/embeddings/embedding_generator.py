"""Embedding generation orchestration for prepared chunks."""

from __future__ import annotations

import time
from collections.abc import Iterable

from lexrag.config import get_settings
from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.embeddings.embedding_backend import EmbeddingBackend
from lexrag.ingestion.embeddings.embedding_cache import EmbeddingCache
from lexrag.ingestion.embeddings.embedding_preparation_service import (
    EmbeddingPreparationService,
)
from lexrag.ingestion.embeddings.schemas.embedding_generation_config import (
    EmbeddingGenerationConfig,
)
from lexrag.ingestion.embeddings.vector_normalizer import normalize
from lexrag.observability.logging_runtime import get_logger

logger = get_logger(__name__)


class EmbeddingGenerator:
    """Production-grade embedding generator with caching and provenance."""

    def __init__(
        self,
        *,
        config: EmbeddingGenerationConfig | None = None,
        backend: EmbeddingBackend,
        cache: EmbeddingCache | None = None,
        preparation_service: EmbeddingPreparationService | None = None,
    ) -> None:
        settings = get_settings()
        self.config = config or EmbeddingGenerationConfig(
            model_name=backend.model_name,
            model_version=backend.model_version,
            batch_size=settings.EMBED_BATCH_SIZE,
            expected_dimension=backend.dimension,
        )
        self.backend = backend
        self.cache = cache or EmbeddingCache()
        self.preparation_service = preparation_service or EmbeddingPreparationService()
        self._validate_backend_dimension()

    @property
    def dimension(self) -> int:
        """Return the active embedding dimension."""
        return self.backend.dimension

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        """Embed raw texts with batching, retries, and caching."""
        payload = [text.strip() for text in texts if text.strip()]
        if not payload:
            return []
        started_at = time.perf_counter()
        vectors = self._embed_payload(payload=payload)
        self._log_stats(total=len(payload), started_at=started_at)
        return vectors

    def embed_query(self, query: str) -> list[float]:
        """Embed a query string using the same backend as chunk embeddings."""
        vectors = self.embed_texts([query])
        if not vectors:
            return [0.0] * self.dimension
        return vectors[0]

    def embed_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Prepare and embed chunks while recording embedding provenance."""
        prepared = self.preparation_service.prepare_chunks(chunks)
        texts = [chunk.embedding_text or chunk.text for chunk in prepared]
        vectors = self.embed_texts(texts)
        return [
            self._embedded_chunk(chunk=chunk, vector=vector)
            for chunk, vector in zip(prepared, vectors, strict=True)
        ]

    def _embed_payload(self, *, payload: list[str]) -> list[list[float]]:
        """Embed a payload list using cache-aware batching."""
        vectors: list[list[float] | None] = [None] * len(payload)
        missing_indices: list[int] = []
        for index, text in enumerate(payload):
            cached = self.cache.get(text=text)
            if cached is not None:
                vectors[index] = cached
                continue
            missing_indices.append(index)
        self._fill_missing_vectors(
            payload=payload,
            vectors=vectors,
            missing_indices=missing_indices,
        )
        return [vector for vector in vectors if vector is not None]

    def _fill_missing_vectors(
        self,
        *,
        payload: list[str],
        vectors: list[list[float] | None],
        missing_indices: list[int],
    ) -> None:
        """Embed uncached texts in batches and update the cache."""
        for start in range(0, len(missing_indices), self.config.batch_size):
            batch_indices = missing_indices[start : start + self.config.batch_size]
            batch_texts = [payload[index] for index in batch_indices]
            batch_vectors = self._retry_embed(batch_texts=batch_texts)
            for index, vector in zip(batch_indices, batch_vectors, strict=True):
                vectors[index] = vector
                self.cache.set(text=payload[index], vector=vector)

    def _retry_embed(self, *, batch_texts: list[str]) -> list[list[float]]:
        """Embed one batch with exponential backoff for transient failures."""
        for attempt in range(1, self.config.max_retries + 1):
            try:
                raw_vectors = self.backend.embed_texts(batch_texts)
                return [self._validated_vector(vector=vector) for vector in raw_vectors]
            except Exception:
                if attempt == self.config.max_retries:
                    raise
                delay = self.config.retry_base_seconds * (2 ** (attempt - 1))
                time.sleep(delay)
        raise RuntimeError("unreachable retry state")

    def _validated_vector(self, *, vector: list[float]) -> list[float]:
        """Validate and normalize backend output vectors."""
        if (
            self.config.expected_dimension is not None
            and len(vector) != self.config.expected_dimension
        ):
            raise ValueError("embedding dimension mismatch")
        return normalize([float(value) for value in vector])

    def _embedded_chunk(self, *, chunk: Chunk, vector: list[float]) -> Chunk:
        """Attach vectors and embedding provenance to one canonical chunk."""
        metadata = chunk.metadata.model_copy(
            update={
                "embedding_model": self.backend.model_name,
                "embedding_model_version": self.backend.model_version,
            }
        )
        return chunk.model_copy(update={"embedding": vector, "metadata": metadata})

    def _log_stats(self, *, total: int, started_at: float) -> None:
        """Log throughput metrics for observability."""
        elapsed = max(time.perf_counter() - started_at, 1e-9)
        logger.info(
            "Embedding complete: total=%d batches=%d wall_time=%.3fs chunks_per_sec=%.2f",
            total,
            self._batch_count(total=total),
            elapsed,
            total / elapsed,
        )

    def _batch_count(self, *, total: int) -> int:
        """Return the number of backend batches for observability logs."""
        return max((total + self.config.batch_size - 1) // self.config.batch_size, 1)

    def _validate_backend_dimension(self) -> None:
        """Validate backend dimension against the configured expectation."""
        if self.config.expected_dimension is None:
            return
        if self.backend.dimension != self.config.expected_dimension:
            raise ValueError("backend dimension does not match configured expectation")
