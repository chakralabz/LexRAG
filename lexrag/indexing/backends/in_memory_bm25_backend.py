"""In-memory BM25 backend for tests and offline evaluation."""

from __future__ import annotations

import math
from collections import Counter
from threading import RLock
from typing import Any

from lexrag.indexing.backends.metadata_filters import matches_metadata_filters
from lexrag.indexing.backends.sparse_store_backend import SparseStoreBackend
from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.utils.text import TextNormalizer


class InMemoryBM25Backend(SparseStoreBackend):
    """Provide deterministic lexical retrieval without external services."""

    def __init__(self, *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._chunks: dict[str, Chunk] = {}
        self._doc_term_freqs: dict[str, Counter[str]] = {}
        self._doc_lengths: dict[str, int] = {}
        self._document_frequencies: Counter[str] = Counter()
        self._avg_doc_len = 0.0
        self._lock = RLock()
        self._tokenizer = TextNormalizer()
        self._metadata_indexes: list[str] = []

    def index_chunks(self, chunks: list[Chunk]) -> int:
        with self._lock:
            for chunk in chunks:
                self._chunks[chunk.chunk_id] = chunk
            self._rebuild_statistics()
        return len(chunks)

    def search_bm25(
        self,
        query: str,
        *,
        limit: int,
        metadata_filters: dict[str, Any] | None,
    ) -> list[Chunk]:
        if limit <= 0:
            return []
        query_terms = self._tokenizer.tokenize_words(query)
        if not query_terms:
            return []
        with self._lock:
            scored = self._score_chunks(
                query_terms=query_terms,
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
            if deleted:
                self._rebuild_statistics()
        return deleted

    def count(self) -> int:
        with self._lock:
            return len(self._chunks)

    def ensure_metadata_indexes(self, fields: list[str]) -> list[str]:
        self._metadata_indexes = list(fields)
        return list(self._metadata_indexes)

    def _rebuild_statistics(self) -> None:
        self._doc_term_freqs.clear()
        self._doc_lengths.clear()
        self._document_frequencies.clear()
        total_len = 0
        for chunk_id, chunk in self._chunks.items():
            tokens = self._tokenizer.tokenize_words(chunk.text)
            term_freq = Counter(tokens)
            self._doc_term_freqs[chunk_id] = term_freq
            doc_len = len(tokens)
            self._doc_lengths[chunk_id] = doc_len
            total_len += doc_len
            for term in term_freq:
                self._document_frequencies[term] += 1
        self._avg_doc_len = total_len / len(self._chunks) if self._chunks else 0.0

    def _score_chunks(
        self,
        *,
        query_terms: list[str],
        metadata_filters: dict[str, Any] | None,
    ) -> list[tuple[float, Chunk]]:
        scored: list[tuple[float, Chunk]] = []
        total_docs = max(len(self._chunks), 1)
        avg_doc_len = self._avg_doc_len or 1.0
        for chunk_id, chunk in self._chunks.items():
            if not matches_metadata_filters(
                chunk=chunk,
                metadata_filters=metadata_filters,
            ):
                continue
            score = self._bm25_score(
                chunk_id=chunk_id,
                query_terms=query_terms,
                total_docs=total_docs,
                avg_doc_len=avg_doc_len,
            )
            scored.append((score, chunk))
        return scored

    def _bm25_score(
        self,
        *,
        chunk_id: str,
        query_terms: list[str],
        total_docs: int,
        avg_doc_len: float,
    ) -> float:
        score = 0.0
        term_freqs = self._doc_term_freqs.get(chunk_id, Counter())
        doc_len = self._doc_lengths.get(chunk_id, 0) or 1
        for term in query_terms:
            term_freq = term_freqs.get(term, 0)
            if term_freq == 0:
                continue
            document_frequency = self._document_frequencies.get(term, 0)
            numerator = total_docs - document_frequency + 0.5
            denominator = document_frequency + 0.5
            idf = math.log(1.0 + numerator / denominator)
            norm = 1 - self.b + self.b * (doc_len / avg_doc_len)
            score += idf * (term_freq * (self.k1 + 1)) / (term_freq + self.k1 * norm)
        return score
