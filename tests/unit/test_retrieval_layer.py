from __future__ import annotations

from lexrag.indexing.bm25_store import BM25Store
from lexrag.vector.qdrant_store import QdrantStore
from lexrag.indexing.schemas import Chunk, ChunkMetadata
from lexrag.ingestion.embedder import build_embedder
from lexrag.retrieval import (
    DenseRetriever,
    HybridRetriever,
    HybridRetrieverConfig,
    QueryDecomposer,
    SparseRetriever,
    TokenOverlapReranker,
)


def _make_chunk(
    *,
    chunk_id: str,
    text: str,
    doc_type: str = "research_paper",
    quality: float = 0.8,
    page_start: int = 1,
    chunk_index: int = 0,
) -> Chunk:
    metadata = ChunkMetadata(
        doc_id="doc_a",
        source_path="/tmp/doc_a.pdf",
        doc_type=doc_type,
        page_start=page_start,
        page_end=page_start,
        section_title="Section",
        chunk_index=chunk_index,
        total_chunks=3,
        chunk_quality_score=quality,
    )
    return Chunk(chunk_id=chunk_id, text=text, metadata=metadata)


def _build_retrievers() -> tuple[DenseRetriever, SparseRetriever]:
    embedder = build_embedder(mode="deterministic-test-only")
    dense_store = QdrantStore(collection_name="unit_dense_v2", backend="memory")
    sparse_store = BM25Store(index_name="unit_sparse_v2", backend="memory")
    chunks = [
        _make_chunk(
            chunk_id="doca_0",
            text="contract obligations and remedies",
            doc_type="contract",
            quality=0.6,
            chunk_index=0,
        ),
        _make_chunk(
            chunk_id="doca_1",
            text="liability damages negligence law",
            doc_type="contract",
            quality=0.9,
            page_start=2,
            chunk_index=1,
        ),
        _make_chunk(
            chunk_id="doca_2",
            text="neural networks transformers optimization",
            doc_type="research_paper",
            quality=0.2,
            chunk_index=2,
        ),
    ]
    embedded_chunks = embedder.embed_chunks(chunks)
    dense_store.upsert_chunks(embedded_chunks)
    sparse_store.index_chunks(embedded_chunks)
    return (
        DenseRetriever(store=dense_store, embedder=embedder),
        SparseRetriever(store=sparse_store),
    )


def test_dense_retriever_applies_rich_metadata_filters() -> None:
    dense, _ = _build_retrievers()
    results = dense.retrieve(
        "liability damages",
        top_k=3,
        metadata_filters={
            "document_type": {"eq": "contract"},
            "chunk_quality_score": {"gte": 0.7},
            "page": {"in": [2]},
        },
    )
    assert [chunk.chunk_id for chunk in results] == ["doca_1"]
    retrieval_payload = results[0].metadata.metadata["retrieval"]
    assert retrieval_payload["source"] == "dense"
    assert retrieval_payload["rank"] == 1


def test_hybrid_retriever_prefers_shared_candidates() -> None:
    dense, sparse = _build_retrievers()
    hybrid = HybridRetriever(
        dense_retriever=dense,
        sparse_retriever=sparse,
        config=HybridRetrieverConfig(top_k=2, prefetch_k=3, rrf_k=60),
    )
    results = hybrid.retrieve("liability damages", top_k=2)
    assert len(results) == 2
    assert results[0].chunk_id == "doca_1"
    retrieval_payload = results[0].metadata.metadata["retrieval"]
    assert retrieval_payload["source"] == "hybrid"
    assert retrieval_payload["dense_rank"] == 1.0
    assert retrieval_payload["sparse_rank"] == 1.0


def test_query_decomposer_returns_single_query_for_factoid() -> None:
    decomposer = QueryDecomposer()
    question = "What are the negligence standards in tort law?"
    assert decomposer.is_multihop(question) is False
    assert decomposer.decompose(question) == [question]


def test_token_overlap_reranker_emits_rank_metadata() -> None:
    reranker = TokenOverlapReranker()
    dense, _ = _build_retrievers()
    retrieved = dense.retrieve("liability damages", top_k=2)
    reranked = reranker.rerank("liability damages in negligence", retrieved, top_k=2)
    assert reranked[0].chunk_id == "doca_1"
    reranker_payload = reranked[0].metadata.metadata["reranker"]
    assert reranker_payload["reranker_score"] > 0
    assert reranker_payload["reranker_rank"] == 1.0
