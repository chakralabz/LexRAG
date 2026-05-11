from __future__ import annotations

import pytest

from lexrag.indexing.bm25_store import BM25Store
from lexrag.indexing.coordinated_index_writer import CoordinatedIndexWriter
from lexrag.vector.qdrant_store import QdrantStore
from lexrag.indexing.schemas import Chunk, ChunkMetadata


def _chunk(
    *,
    chunk_id: str,
    doc_id: str,
    version: str,
    embedding: list[float],
) -> Chunk:
    metadata = ChunkMetadata(
        doc_id=doc_id,
        document_version=version,
        source_path=f"/tmp/{doc_id}.pdf",
        doc_type="contract",
        page_num=1,
        section_title="Section",
        chunk_index=0,
        total_chunks=1,
    )
    return Chunk(
        chunk_id=chunk_id,
        text=f"text for {chunk_id}",
        metadata=metadata,
        embedding=embedding,
    )


def test_index_writer_replaces_sparse_and_dense_versions_together() -> None:
    dense_store = QdrantStore(collection_name="coord_dense", backend="memory")
    sparse_store = BM25Store(index_name="coord_sparse", backend="memory")
    writer = CoordinatedIndexWriter(
        qdrant_store=dense_store,
        bm25_store=sparse_store,
    )
    old_chunk = _chunk(
        chunk_id="doc_a_v1",
        doc_id="doc_a",
        version="v1",
        embedding=[1.0, 0.0, 0.0],
    )
    new_chunk = _chunk(
        chunk_id="doc_a_v2",
        doc_id="doc_a",
        version="v2",
        embedding=[0.9, 0.1, 0.0],
    )

    writer.index_chunks([old_chunk])
    writer.index_chunks([new_chunk])

    dense_ids = [
        chunk.chunk_id
        for chunk in dense_store.list_document_chunks(document_id="doc_a")
    ]
    sparse_ids = [
        chunk.chunk_id
        for chunk in sparse_store.list_document_chunks(document_id="doc_a")
    ]
    assert dense_ids == ["doc_a_v2"]
    assert sparse_ids == ["doc_a_v2"]


def test_index_writer_rolls_back_dense_and_sparse_when_sparse_write_fails() -> None:
    dense_store = QdrantStore(collection_name="coord_dense_rb", backend="memory")
    sparse_store = BM25Store(index_name="coord_sparse_rb", backend="memory")
    writer = CoordinatedIndexWriter(
        qdrant_store=dense_store,
        bm25_store=sparse_store,
    )
    old_chunk = _chunk(
        chunk_id="doc_a_v1",
        doc_id="doc_a",
        version="v1",
        embedding=[1.0, 0.0, 0.0],
    )
    new_chunk = _chunk(
        chunk_id="doc_a_v2",
        doc_id="doc_a",
        version="v2",
        embedding=[0.9, 0.1, 0.0],
    )

    writer.index_chunks([old_chunk])
    replace_document = sparse_store.replace_document_chunks

    def fail_after_partial_write(*, document_id: str, chunks: list[Chunk]) -> int:
        replace_document(document_id=document_id, chunks=chunks)
        raise RuntimeError("sparse write failed")

    sparse_store.replace_document_chunks = fail_after_partial_write  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="sparse write failed"):
        writer.index_chunks([new_chunk])

    dense_ids = [
        chunk.chunk_id
        for chunk in dense_store.list_document_chunks(document_id="doc_a")
    ]
    sparse_ids = [
        chunk.chunk_id
        for chunk in sparse_store.list_document_chunks(document_id="doc_a")
    ]
    assert dense_ids == ["doc_a_v1"]
    assert sparse_ids == ["doc_a_v1"]
