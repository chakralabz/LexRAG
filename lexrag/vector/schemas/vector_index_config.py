"""Configuration for the dense vector store facade."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VectorIndexConfig(BaseModel):
    """Runtime configuration for vector persistence.

    Attributes:
        collection_name: Logical collection name for stored embeddings.
        backend: Backend implementation identifier.
        vector_size: Expected embedding dimensionality. When unset, the first
            successful write establishes the dimension contract.
        qdrant_url: Qdrant service URL for the service-backed backend.
        api_key: Optional Qdrant API key.
        metadata_index_fields: Metadata fields that must remain filterable.
    """

    model_config = ConfigDict(frozen=True)

    collection_name: str = Field(default="lexrag_chunks")
    backend: str = Field(default="qdrant")
    vector_size: int | None = Field(default=None, ge=1)
    qdrant_url: str = Field(default="http://localhost:6333")
    api_key: str | None = Field(default=None)
    metadata_index_fields: tuple[str, ...] = Field(
        default=("doc_id", "doc_type", "page_start", "chunk_type", "document_version")
    )
