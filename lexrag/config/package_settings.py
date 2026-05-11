"""Validated SDK settings for reusable LexRAG deployments."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LexRAGSettings(BaseModel):
    """Flat runtime settings shared by package-level services."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    environment: Literal["DEV", "TEST", "PROD"] = Field(default="DEV")
    log_level: str = Field(default="INFO")
    log_format: Literal["text", "json"] = Field(default="text")
    embed_model: str = Field(default="BAAI/bge-m3")
    rerank_model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-12-v2")
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_collection: str = Field(default="lexrag_chunks")
    elasticsearch_url: str = Field(default="http://localhost:9200")
    elasticsearch_index: str = Field(default="lexrag_chunks")
    embed_batch_size: int = Field(default=32, ge=1)
    min_chunk_tokens: int = Field(default=128, ge=1)
    max_chunk_tokens: int = Field(default=512, ge=1)
    semantic_chunk_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    retrieval_top_k: int = Field(default=10, ge=1)
    retriever_top_n: int = Field(default=20, ge=1)
    config_path: Path | None = Field(default=None)
