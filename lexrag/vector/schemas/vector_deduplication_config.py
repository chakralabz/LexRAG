"""Configuration for vector-level duplicate handling."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VectorDeduplicationConfig(BaseModel):
    """Policy knobs for semantic deduplication after embedding.

    Attributes:
        within_document_similarity_threshold: Similarity threshold that
            suppresses duplicate chunks inside the same document lineage.
        cross_document_similarity_threshold: Similarity threshold that logs a
            cross-document near-duplicate while preserving both chunks.
        candidate_pool_size: Number of nearest-neighbor candidates inspected
            from the existing vector index for each incoming chunk.
        require_matching_doc_id_for_suppression: Restricts suppression to the
            same `doc_id` lineage when `True`.
    """

    model_config = ConfigDict(frozen=True)

    within_document_similarity_threshold: float = Field(
        default=0.98,
        ge=0.0,
        le=1.0,
    )
    cross_document_similarity_threshold: float = Field(
        default=0.97,
        ge=0.0,
        le=1.0,
    )
    candidate_pool_size: int = Field(default=12, ge=1, le=256)
    require_matching_doc_id_for_suppression: bool = Field(default=True)
