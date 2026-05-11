"""Configuration schema for sparse lexical storage."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SparseIndexConfig(BaseModel):
    """Runtime configuration for the sparse index facade.

    Attributes:
        index_name: Logical index name for keyword retrieval.
        backend: Backend implementation identifier.
        elasticsearch_url: Elasticsearch endpoint for production-style sparse
            retrieval.
        metadata_index_fields: Metadata fields expected to remain filterable.
    """

    model_config = ConfigDict(frozen=True)

    index_name: str = Field(default="lexrag_chunks")
    backend: str = Field(default="elasticsearch")
    elasticsearch_url: str = Field(default="http://localhost:9200")
    metadata_index_fields: tuple[str, ...] = Field(
        default=("doc_id", "doc_type", "page_start", "chunk_type", "document_version")
    )
