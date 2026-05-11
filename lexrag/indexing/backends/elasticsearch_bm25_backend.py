"""Elasticsearch-backed sparse storage adapter."""

from __future__ import annotations

from typing import Any

from lexrag.indexing.backends.bm25_document_mapper import (
    build_document,
    chunk_from_document,
)
from lexrag.indexing.backends.sparse_store_backend import SparseStoreBackend
from lexrag.ingestion.chunker.schemas.chunk import Chunk


class ElasticsearchBM25Backend(SparseStoreBackend):
    """Persist sparse retrieval artifacts in Elasticsearch."""

    def __init__(self, *, index_name: str, elasticsearch_url: str) -> None:
        self._client, self._bulk = self._build_client(
            elasticsearch_url=elasticsearch_url
        )
        self._index_name = index_name
        self._ensure_index()

    def index_chunks(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        actions = self._build_actions(chunks=chunks)
        self._bulk(self._client, actions)
        self._client.indices.refresh(index=self._index_name)
        return len(chunks)

    def search_bm25(
        self,
        query: str,
        *,
        limit: int,
        metadata_filters: dict[str, Any] | None,
    ) -> list[Chunk]:
        if limit <= 0 or not query.strip():
            return []
        response = self._client.search(
            index=self._index_name,
            size=limit,
            query={
                "bool": {
                    "must": [{"match": {"text": query}}],
                    "filter": self._filter_clauses(metadata_filters=metadata_filters),
                }
            },
        )
        hits = response.get("hits", {}).get("hits", [])
        return [self._chunk_from_hit(hit=hit) for hit in hits]

    def list_chunks(
        self,
        *,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        response = self._client.search(
            index=self._index_name,
            size=10_000,
            query={
                "bool": {
                    "filter": self._filter_clauses(
                        metadata_filters=metadata_filters,
                    )
                }
            },
        )
        hits = response.get("hits", {}).get("hits", [])
        return [self._chunk_from_hit(hit=hit) for hit in hits]

    def delete_chunks(self, chunk_ids: list[str]) -> int:
        if not chunk_ids:
            return 0
        actions = self._delete_actions(chunk_ids=chunk_ids)
        self._bulk(self._client, actions)
        self._client.indices.refresh(index=self._index_name)
        return len(chunk_ids)

    def count(self) -> int:
        response = self._client.count(index=self._index_name)
        return int(response.get("count", 0))

    def ensure_metadata_indexes(self, fields: list[str]) -> list[str]:
        if not fields:
            return []
        properties = {f"metadata.{field}": {"type": "keyword"} for field in fields}
        self._client.indices.put_mapping(index=self._index_name, properties=properties)
        return list(fields)

    def _build_client(self, *, elasticsearch_url: str) -> tuple[Any, Any]:
        try:
            from elasticsearch import Elasticsearch
            from elasticsearch.helpers import bulk
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "elasticsearch package is required for Elasticsearch backend"
            ) from exc
        return Elasticsearch(elasticsearch_url), bulk

    def _ensure_index(self) -> None:
        if self._client.indices.exists(index=self._index_name):
            return
        self._client.indices.create(
            index=self._index_name,
            mappings={
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "text": {"type": "text"},
                    "embedding_text": {"type": "text"},
                    "metadata": {"type": "object", "dynamic": True},
                }
            },
        )

    def _build_actions(self, *, chunks: list[Chunk]) -> list[dict[str, object]]:
        return [
            {
                "_op_type": "index",
                "_index": self._index_name,
                "_id": chunk.chunk_id,
                **build_document(chunk=chunk),
            }
            for chunk in chunks
        ]

    def _delete_actions(self, *, chunk_ids: list[str]) -> list[dict[str, object]]:
        return [
            {
                "_op_type": "delete",
                "_index": self._index_name,
                "_id": chunk_id,
            }
            for chunk_id in chunk_ids
        ]

    def _filter_clauses(
        self,
        *,
        metadata_filters: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        return [
            {"term": {f"metadata.{field}": value}}
            for field, value in (metadata_filters or {}).items()
        ]

    def _chunk_from_hit(self, *, hit: dict[str, object]) -> Chunk:
        raw_source = hit.get("_source")
        source = raw_source if isinstance(raw_source, dict) else {}
        return chunk_from_document(source=source)
