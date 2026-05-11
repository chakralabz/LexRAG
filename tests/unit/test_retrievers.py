from __future__ import annotations

from lexrag.indexing.bm25_store import BM25Store
from lexrag.vector.qdrant_store import QdrantStore
from lexrag.indexing.schemas import Chunk, ChunkMetadata

from lexrag.ingestion.embedder import build_embedder
from lexrag.retrieval import (
    DenseRetriever,
    HybridRetriever,
    HybridRetrieverConfig,
    SparseRetriever,
)


def _make_chunk(*, chunk_id: str, text: str, chunk_index: int) -> Chunk:
    metadata = ChunkMetadata(
        doc_id="doc_a",
        source_path="/tmp/doc_a.pdf",
        doc_type="research_paper",
        page_num=1,
        section_title="Section",
        chunk_index=chunk_index,
        total_chunks=3,
    )
    return Chunk(chunk_id=chunk_id, text=text, metadata=metadata)


def _indexed_retrievers() -> tuple[DenseRetriever, SparseRetriever]:
    embedder = build_embedder(mode="deterministic-test-only")
    dense_store = QdrantStore(collection_name="unit_dense", backend="memory")
    sparse_store = BM25Store(index_name="unit_sparse", backend="memory")
    chunks = [
        _make_chunk(
            chunk_id="doca_0", text="contract obligations and remedies", chunk_index=0
        ),
        _make_chunk(
            chunk_id="doca_1", text="liability damages negligence law", chunk_index=1
        ),
        _make_chunk(
            chunk_id="doca_2",
            text="neural networks transformers optimization",
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


def test_sparse_retriever_exact_match_ranking() -> None:
    _, sparse = _indexed_retrievers()
    results = sparse.retrieve("liability damages", top_k=2)
    assert len(results) == 2
    assert results[0].chunk_id == "doca_1"


def test_hybrid_retriever_can_reduce_to_sparse_mode() -> None:
    dense, sparse = _indexed_retrievers()
    hybrid = HybridRetriever(
        dense_retriever=dense,
        sparse_retriever=sparse,
        config=HybridRetrieverConfig(
            top_k=2,
            prefetch_k=3,
            rrf_k=60,
            dense_weight=0.0,
            sparse_weight=1.0,
        ),
    )

    hybrid_results = hybrid.retrieve("liability damages", top_k=2)
    sparse_results = sparse.retrieve("liability damages", top_k=2)
    assert [chunk.chunk_id for chunk in hybrid_results] == [
        chunk.chunk_id for chunk in sparse_results
    ]
