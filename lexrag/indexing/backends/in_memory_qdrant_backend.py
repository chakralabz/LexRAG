"""In-memory dense backend used by tests and offline workflows."""

from __future__ import annotations

from threading import RLock
from typing import Any

from lexrag.indexing.backends.dense_store_backend import DenseStoreBackend
from lexrag.indexing.backends.metadata_filters import matches_metadata_filters
from lexrag.indexing.backends.vector_math import cosine_similarity
from lexrag.ingestion.chunker.schemas.chunk import Chunk


class InMemoryQdrantBackend(DenseStoreBackend):
    """Provide deterministic dense retrieval without external services."""

    def __init__(self) -> None:
        self._chunks: dict[str, Chunk] = {}
        self._lock = RLock()
        self._metadata_indexes: list[str] = []

    def upsert_chunks(self, chunks: list[Chunk]) -> int:
        with self._lock:
            for chunk in chunks:
                self._validate_embedding(chunk=chunk)
                self._chunks[chunk.chunk_id] = chunk
        return len(chunks)

    def search_dense(
        self,
        query_vector: list[float],
        *,
        limit: int,
        metadata_filters: dict[str, Any] | None,
    ) -> list[Chunk]:
        if limit <= 0:
            return []
        with self._lock:
            scored = self._score_chunks(
                query_vector=query_vector,
                metadata_filters=metadata_filters,
            )
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[:limit]]

    def list_chunks(
        self,
        *,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        with self._lock:
            return [
                chunk
                for chunk in self._chunks.values()
                if matches_metadata_filters(
                    chunk=chunk,
                    metadata_filters=metadata_filters,
                )
            ]

    def delete_chunks(self, chunk_ids: list[str]) -> int:
        deleted = 0
        with self._lock:
            for chunk_id in chunk_ids:
                if self._chunks.pop(chunk_id, None) is not None:
                    deleted += 1
        return deleted

    def delete_collection(self) -> None:
        with self._lock:
            self._chunks.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._chunks)

    def ensure_metadata_indexes(self, fields: list[str]) -> list[str]:
        self._metadata_indexes = list(fields)
        return list(self._metadata_indexes)

    def _score_chunks(
        self,
        *,
        query_vector: list[float],
        metadata_filters: dict[str, Any] | None,
    ) -> list[tuple[float, Chunk]]:
        scored: list[tuple[float, Chunk]] = []
        for chunk in self._chunks.values():
            if not matches_metadata_filters(
                chunk=chunk,
                metadata_filters=metadata_filters,
            ):
                continue
            similarity = cosine_similarity(query_vector, chunk.embedding or [])
            scored.append((similarity, chunk))
        return scored

    def _validate_embedding(self, *, chunk: Chunk) -> None:
        if chunk.embedding is None:
            raise ValueError(f"Chunk {chunk.chunk_id} is missing embedding")
