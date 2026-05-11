"""Indexer that builds retrieval artifacts for eval runs."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import cast

from tqdm import tqdm

from lexrag.eval.indexed_corpus import IndexedCorpus
from lexrag.eval.retrieval_mode import RetrievalMode
from lexrag.indexing.bm25_store import BM25Store
from lexrag.vector.qdrant_store import QdrantStore
from lexrag.indexing.schemas import Chunk
from lexrag.ingestion.chunker import Chunker
from lexrag.ingestion.embedder import BGEEmbedder
from lexrag.ingestion.normalizer import BlockNormalizer
from lexrag.ingestion.page_enricher import (
    PagePayloadEnricher,
    StaticDocumentTypeResolver,
)
from lexrag.ingestion.parser import FallbackDocumentParser, ParsedBlock
from lexrag.retrieval import (
    DenseRetriever,
    HybridRetriever,
    HybridRetrieverConfig,
    Retriever,
    SparseRetriever,
)
from lexrag.observability.logging_runtime import get_logger

logger = get_logger(__name__)


class EvalIndexer:
    """Builds retrieval artifacts from source documents."""

    def __init__(
        self,
        *,
        parser: FallbackDocumentParser,
        chunker: Chunker,
        embedder: BGEEmbedder,
        dense_store: QdrantStore,
        sparse_store: BM25Store | None,
        retrieval_mode: RetrievalMode,
        normalizer: BlockNormalizer | None = None,
    ) -> None:
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder
        self.dense_store = dense_store
        self.sparse_store = sparse_store
        self.retrieval_mode = retrieval_mode
        self.normalizer = normalizer or BlockNormalizer()
        self.page_enricher = PagePayloadEnricher(
            resolver=StaticDocumentTypeResolver(doc_type="research_paper")
        )
        self._fallback_reason_counts: Counter[str] = Counter()
        self._parse_failure_counts: Counter[str] = Counter()

    def build(self, *, input_dir: Path, limit_docs: int | None) -> IndexedCorpus:
        """Indexes corpus and returns retriever + chunk metadata artifacts."""
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
        paths = self._discover_paths(input_dir=input_dir, limit_docs=limit_docs)
        embedded = self._build_embedded_chunks(paths)
        self._index_chunks(embedded)
        return IndexedCorpus(
            chunks=embedded,
            chunk_ids_by_doc=self._group_chunk_ids_by_doc(embedded),
            retriever=self._build_retriever(),
            num_docs_ingested=len({chunk.metadata.doc_id for chunk in embedded}),
            fallback_reason_counts=dict(self._fallback_reason_counts),
            parse_failure_counts=dict(self._parse_failure_counts),
        )

    def _discover_paths(self, *, input_dir: Path, limit_docs: int | None) -> list[Path]:
        paths = [
            path
            for path in sorted(input_dir.rglob("*"))
            if path.is_file() and path.suffix.lower() in {".pdf", ".html", ".htm"}
        ]
        if limit_docs is not None:
            paths = paths[:limit_docs]
        return paths

    def _build_embedded_chunks(self, paths: list[Path]) -> list[Chunk]:
        all_chunks: list[Chunk] = []
        self._fallback_reason_counts.clear()
        self._parse_failure_counts.clear()
        for path in tqdm(paths, desc="Parsing documents", unit="doc"):
            parsed = self._safe_parse(path=path)
            if not parsed:
                continue
            self._record_parser_provenance(parsed=parsed)
            pages = cast(
                list[ParsedBlock], self.page_enricher.enrich(parsed, path=path)
            )
            normalized = self.normalizer.normalize(pages)
            all_chunks.extend(self.chunker.chunk(normalized))
        self._log_parse_summary()
        return self.embedder.embed_chunks(all_chunks)

    def _safe_parse(self, *, path: Path) -> list[ParsedBlock]:
        """Parse one document path and continue eval on per-file failures."""
        try:
            return self.parser.parse_document(path)
        except Exception as exc:
            reason = self._classify_parse_failure(exc=exc)
            self._parse_failure_counts[reason] += 1
            logger.warning(
                "Skipping parse failure for %s reason=%s: %s", path, reason, exc
            )
            return []

    def _record_parser_provenance(self, *, parsed: list[ParsedBlock]) -> None:
        """Collect fallback and primary error provenance from parsed blocks."""
        if not parsed:
            return
        metadata = parsed[0].metadata or {}
        reason = metadata.get("fallback_reason_code")
        if isinstance(reason, str) and reason:
            self._fallback_reason_counts[reason] += 1
        error_type = metadata.get("primary_error_type")
        if isinstance(error_type, str) and error_type:
            self._parse_failure_counts[error_type] += 1

    def _classify_parse_failure(self, *, exc: Exception) -> str:
        """Map parsing exceptions to stable reason labels for eval observability."""
        message = str(exc).lower()
        if isinstance(exc, FileNotFoundError):
            return "file_not_found"
        if "unsupported document type" in message:
            return "unsupported_document_type"
        if "empty" in message:
            return "empty_content"
        if "pymupdf is required" in message:
            return "fallback_dependency_missing"
        return exc.__class__.__name__

    def _log_parse_summary(self) -> None:
        """Emit aggregated parser provenance summary for eval runs."""
        logger.info(
            "Eval parse summary fallback_reasons=%s parse_failures=%s",
            dict(self._fallback_reason_counts),
            dict(self._parse_failure_counts),
        )

    def _index_chunks(self, chunks: list[Chunk]) -> None:
        self.dense_store.upsert_chunks(chunks)
        if self.sparse_store is not None:
            self.sparse_store.index_chunks(chunks)

    def _group_chunk_ids_by_doc(self, chunks: list[Chunk]) -> dict[str, list[str]]:
        chunk_ids_by_doc: dict[str, list[str]] = {}
        for chunk in chunks:
            doc_id = chunk.metadata.doc_id or "unknown_doc"
            chunk_ids_by_doc.setdefault(doc_id, []).append(chunk.chunk_id)
        return chunk_ids_by_doc

    def _build_retriever(self) -> Retriever:
        dense_retriever = DenseRetriever(store=self.dense_store, embedder=self.embedder)
        if self.retrieval_mode == "dense":
            return dense_retriever
        if self.sparse_store is None:
            raise ValueError("Sparse store is required for hybrid retrieval mode")
        sparse_retriever = SparseRetriever(store=self.sparse_store)
        return HybridRetriever(
            dense_retriever=dense_retriever,
            sparse_retriever=sparse_retriever,
            config=HybridRetrieverConfig(top_k=10, prefetch_k=40, rrf_k=60),
        )
