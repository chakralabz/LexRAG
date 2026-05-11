"""Indexed corpus artifact model for eval runs."""

from __future__ import annotations

from dataclasses import dataclass

from lexrag.indexing.schemas import Chunk
from lexrag.retrieval import Retriever


@dataclass(frozen=True, slots=True)
class IndexedCorpus:
    """Artifacts built during one eval indexing pass."""

    chunks: list[Chunk]
    chunk_ids_by_doc: dict[str, list[str]]
    retriever: Retriever
    num_docs_ingested: int
    fallback_reason_counts: dict[str, int]
    parse_failure_counts: dict[str, int]
