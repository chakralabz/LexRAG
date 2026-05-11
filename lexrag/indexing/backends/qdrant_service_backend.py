"""Qdrant-backed dense storage adapter."""

from __future__ import annotations

from typing import Any

from lexrag.indexing.backends.dense_store_backend import DenseStoreBackend
from lexrag.indexing.backends.qdrant_payload_mapper import (
    build_payload,
    chunk_from_payload,
)
from lexrag.ingestion.chunker.schemas.chunk import Chunk


class QdrantServiceBackend(DenseStoreBackend):
    """Persist dense vectors in Qdrant with filterable payload metadata."""

    def __init__(
        self,
        *,
        collection_name: str,
        vector_size: int | None,
        qdrant_url: str,
        api_key: str | None,
    ) -> None:
        self._qmodels = self._load_models()
        self._client = self._build_client(qdrant_url=qdrant_url, api_key=api_key)
        self._collection_name = collection_name
        self._vector_size = vector_size
        if vector_size is not None:
            self._ensure_collection(vector_size=vector_size)

    def upsert_chunks(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        vector_size = self._resolve_vector_size(chunks=chunks)
        self._ensure_collection(vector_size=vector_size)
        points = self._build_points(chunks=chunks)
        self._client.upsert(collection_name=self._collection_name, points=points)
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
        query_filter = self._build_query_filter(metadata_filters=metadata_filters)
        results = self._client.search(
            collection_name=self._collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=True,
        )
        return [self._chunk_from_hit(hit=hit) for hit in results]

    def list_chunks(
        self,
        *,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        query_filter = self._build_query_filter(metadata_filters=metadata_filters)
        points, _ = self._client.scroll(
            collection_name=self._collection_name,
            scroll_filter=query_filter,
            with_payload=True,
            with_vectors=True,
            limit=10_000,
        )
        return [self._chunk_from_hit(hit=point) for point in points]

    def delete_chunks(self, chunk_ids: list[str]) -> int:
        if not chunk_ids:
            return 0
        self._client.delete(
            collection_name=self._collection_name,
            points_selector=self._qmodels.PointIdsList(points=chunk_ids),
        )
        return len(chunk_ids)

    def delete_collection(self) -> None:
        self._client.delete_collection(collection_name=self._collection_name)
        if self._vector_size is not None:
            self._ensure_collection(vector_size=self._vector_size)

    def count(self) -> int:
        response = self._client.count(collection_name=self._collection_name, exact=True)
        return int(response.count)

    def ensure_metadata_indexes(self, fields: list[str]) -> list[str]:
        realized: list[str] = []
        for field in fields:
            self._client.create_payload_index(
                collection_name=self._collection_name,
                field_name=field,
                field_schema=self._qmodels.PayloadSchemaType.KEYWORD,
            )
            realized.append(field)
        return realized

    def _load_models(self) -> Any:
        try:
            from qdrant_client.http import models as qmodels
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("qdrant-client is required for Qdrant backend") from exc
        return qmodels

    def _build_client(self, *, qdrant_url: str, api_key: str | None) -> Any:
        try:
            from qdrant_client import QdrantClient
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("qdrant-client is required for Qdrant backend") from exc
        return QdrantClient(url=qdrant_url, api_key=api_key)

    def _resolve_vector_size(self, *, chunks: list[Chunk]) -> int:
        if self._vector_size is not None:
            return self._vector_size
        first_embedding = chunks[0].embedding or []
        if not first_embedding:
            raise ValueError("Cannot infer vector size from empty embedding")
        self._vector_size = len(first_embedding)
        return self._vector_size

    def _ensure_collection(self, *, vector_size: int) -> None:
        if self._client.collection_exists(self._collection_name):
            return
        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=self._qmodels.VectorParams(
                size=vector_size,
                distance=self._qmodels.Distance.COSINE,
            ),
        )

    def _build_points(self, *, chunks: list[Chunk]) -> list[Any]:
        points: list[Any] = []
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.chunk_id} is missing embedding")
            points.append(
                self._qmodels.PointStruct(
                    id=chunk.chunk_id,
                    vector=chunk.embedding,
                    payload=build_payload(chunk=chunk),
                )
            )
        return points

    def _build_query_filter(self, *, metadata_filters: dict[str, Any] | None) -> Any:
        if not metadata_filters:
            return None
        conditions = [
            self._qmodels.FieldCondition(
                key=field,
                match=self._qmodels.MatchValue(value=value),
            )
            for field, value in metadata_filters.items()
        ]
        return self._qmodels.Filter(must=conditions)

    def _chunk_from_hit(self, *, hit: Any) -> Chunk:
        return chunk_from_payload(
            payload=dict(hit.payload or {}),
            vector=list(hit.vector) if hit.vector is not None else None,
        )
