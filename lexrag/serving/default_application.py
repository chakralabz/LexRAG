"""Default serving-layer dependency builder."""

from __future__ import annotations

from pathlib import Path

from lexrag.config import Settings, get_settings
from lexrag.context_builder import LLMContextBuilder
from lexrag.generation import AnswerGenerator, LLMBackend
from lexrag.indexing.bm25_store import BM25Store
from lexrag.ingestion.chunker.fixed_size_chunker import FixedSizeChunker
from lexrag.ingestion.embedder import build_embedder
from lexrag.ingestion.jobs import IngestJobManager, IngestJobRepository
from lexrag.ingestion.parser import FallbackDocumentParser
from lexrag.ingestion.pipeline import IngestPipeline
from lexrag.observability.logging_runtime import configure_logging
from lexrag.retrieval import DenseRetriever, HybridRetriever, SparseRetriever
from lexrag.serving.lexrag_application import LexRAGApplication
from lexrag.serving.runtime_dependencies import RuntimeDependencies
from lexrag.vector.qdrant_store import QdrantStore


def build_default_application(
    *,
    settings: Settings | None = None,
    llm_backend: LLMBackend | None = None,
) -> LexRAGApplication:
    """Build the standard application wiring for local or production serving."""
    configure_logging()
    resolved = settings or get_settings()
    embedder = build_embedder()
    qdrant_store = _qdrant_store(settings=resolved)
    bm25_store = _bm25_store(settings=resolved)
    dependencies = RuntimeDependencies(
        ingestion_pipeline=_ingestion_pipeline(
            settings=resolved,
            embedder=embedder,
            qdrant_store=qdrant_store,
            bm25_store=bm25_store,
        ),
        ingest_job_manager=_ingest_job_manager(),
        retriever=_retriever(
            embedder=embedder,
            qdrant_store=qdrant_store,
            bm25_store=bm25_store,
        ),
        context_builder=LLMContextBuilder(),
        generator=_generator(llm_backend=llm_backend),
    )
    return LexRAGApplication(
        dependencies=dependencies,
        ingest_root=Path(resolved.INGEST_INPUT_DIR),
        http_ingest_enabled=resolved.LEXRAG_ENABLE_HTTP_INGEST,
    )


def _ingestion_pipeline(
    *,
    settings: Settings,
    embedder,
    qdrant_store: QdrantStore,
    bm25_store: BM25Store,
) -> IngestPipeline:
    return IngestPipeline(
        parser=FallbackDocumentParser(),
        chunker=FixedSizeChunker(chunk_size=settings.MAX_CHUNK_TOKENS, overlap=64),
        embedder=embedder,
        qdrant_store=qdrant_store,
        bm25_store=bm25_store,
    )


def _retriever(
    *,
    embedder,
    qdrant_store: QdrantStore,
    bm25_store: BM25Store,
) -> HybridRetriever:
    dense = DenseRetriever(store=qdrant_store, embedder=embedder)
    sparse = SparseRetriever(store=bm25_store)
    return HybridRetriever(dense_retriever=dense, sparse_retriever=sparse)


def _generator(*, llm_backend: LLMBackend | None) -> AnswerGenerator | None:
    if llm_backend is None:
        return None
    return AnswerGenerator(backend=llm_backend)


def _qdrant_store(*, settings: Settings) -> QdrantStore:
    backend = "qdrant" if settings.LEXRAG_USE_REAL_STORES else "memory"
    return QdrantStore(
        collection_name=settings.QDRANT_COLLECTION,
        backend=backend,
        qdrant_url=settings.QDRANT_URL,
    )


def _bm25_store(*, settings: Settings) -> BM25Store:
    backend = "elasticsearch" if settings.LEXRAG_USE_REAL_STORES else "memory"
    return BM25Store(
        index_name=settings.ELASTICSEARCH_INDEX,
        backend=backend,
        elasticsearch_url=settings.ELASTICSEARCH_URL,
    )


def _ingest_job_manager() -> IngestJobManager:
    repository = IngestJobRepository(root_dir=Path(".lexrag/ingest_jobs"))
    return IngestJobManager(repository=repository)
