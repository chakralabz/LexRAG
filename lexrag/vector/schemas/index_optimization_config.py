"""Configuration for dense and sparse index optimization policy."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class IndexOptimizationConfig(BaseModel):
    """Declarative optimization policy for vector search infrastructure.

    Attributes:
        dense_algorithm: Named ANN strategy used for dense retrieval.
        sparse_strategy: Named sparse retrieval strategy.
        filterable_metadata_fields: Fields that must remain fast for filters.
        payload_retention_fields: Fields intentionally retained in the vector
            payload because retrieval or reranking depends on them.
    """

    model_config = ConfigDict(frozen=True)

    dense_algorithm: str = Field(default="hnsw")
    sparse_strategy: str = Field(default="bm25")
    filterable_metadata_fields: tuple[str, ...] = Field(
        default=("doc_id", "doc_type", "page_start", "chunk_type", "document_version")
    )
    payload_retention_fields: tuple[str, ...] = Field(
        default=(
            "chunk_id",
            "text",
            "embedding_text",
            "doc_id",
            "doc_type",
            "page_start",
            "chunk_type",
            "section_path",
            "document_version",
            "embedding_model",
            "embedding_model_version",
        )
    )
