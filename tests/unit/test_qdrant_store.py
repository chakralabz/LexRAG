from __future__ import annotations

import pytest

from lexrag.vector.qdrant_store import QdrantStore
from lexrag.indexing.schemas import Chunk, ChunkMetadata


def _chunk(
    *,
    chunk_id: str,
    doc_id: str,
    version: str,
    chunk_index: int,
    embedding: list[float],
    doc_type: str = "contract",
) -> Chunk:
    metadata = ChunkMetadata(
        doc_id=doc_id,
        document_version=version,
        source_path=f"/tmp/{doc_id}.pdf",
        doc_type=doc_type,
        page_num=1,
        section_title="Section",
        chunk_index=chunk_index,
        total_chunks=2,
    )
    return Chunk(
        chunk_id=chunk_id,
        text=f"text {chunk_id}",
        metadata=metadata,
        embedding=embedding,
    )


def test_qdrant_store_filters_results_by_metadata() -> None:
    store = QdrantStore(collection_name="unit_dense", backend="memory")
    contract_chunk = _chunk(
        chunk_id="doc_a_0",
        doc_id="doc_a",
        version="v1",
        chunk_index=0,
        embedding=[1.0, 0.0, 0.0],
        doc_type="contract",
    )
    policy_chunk = _chunk(
        chunk_id="doc_b_0",
        doc_id="doc_b",
        version="v1",
        chunk_index=0,
        embedding=[0.0, 1.0, 0.0],
        doc_type="policy",
    )

    store.upsert_chunks([contract_chunk, policy_chunk])
    results = store.search_dense(
        [1.0, 0.0, 0.0],
        limit=5,
        metadata_filters={"doc_type": "contract"},
    )

    assert [chunk.chunk_id for chunk in results] == ["doc_a_0"]


def test_qdrant_store_replaces_stale_document_versions() -> None:
    store = QdrantStore(collection_name="unit_dense_versions", backend="memory")
    old_chunk = _chunk(
        chunk_id="doc_a_old",
        doc_id="doc_a",
        version="v1",
        chunk_index=0,
        embedding=[1.0, 0.0, 0.0],
    )
    new_chunk = _chunk(
        chunk_id="doc_a_new",
        doc_id="doc_a",
        version="v2",
        chunk_index=0,
        embedding=[0.9, 0.1, 0.0],
    )

    store.upsert_chunks([old_chunk])
    store.upsert_chunks([new_chunk])
    remaining = store.search_dense([1.0, 0.0, 0.0], limit=10)

    assert [chunk.chunk_id for chunk in remaining] == ["doc_a_new"]
    assert store.last_upsert_report.replaced_chunks == 1
    assert store.last_upsert_report.reindex_plans[0].stale_chunk_ids == ["doc_a_old"]


def test_qdrant_store_rejects_mismatched_embedding_dimension() -> None:
    store = QdrantStore(
        collection_name="unit_dense_dim",
        backend="memory",
        vector_size=3,
    )
    bad_chunk = _chunk(
        chunk_id="doc_a_bad",
        doc_id="doc_a",
        version="v1",
        chunk_index=0,
        embedding=[1.0, 0.0],
    )

    with pytest.raises(ValueError):
        store.upsert_chunks([bad_chunk])


def test_qdrant_store_restores_previous_document_on_stale_cleanup_failure() -> None:
    store = QdrantStore(collection_name="unit_dense_rollback", backend="memory")
    old_chunk = _chunk(
        chunk_id="doc_a_old",
        doc_id="doc_a",
        version="v1",
        chunk_index=0,
        embedding=[1.0, 0.0, 0.0],
    )
    new_chunk = _chunk(
        chunk_id="doc_a_new",
        doc_id="doc_a",
        version="v2",
        chunk_index=0,
        embedding=[0.9, 0.1, 0.0],
    )

    store.upsert_chunks([old_chunk])
    delete_chunks = store.backend.delete_chunks

    def fail_on_stale_delete(chunk_ids: list[str]) -> int:
        if chunk_ids == ["doc_a_old"]:
            raise RuntimeError("delete failed")
        return delete_chunks(chunk_ids)

    store.backend.delete_chunks = fail_on_stale_delete  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="delete failed"):
        store.upsert_chunks([new_chunk])

    remaining = store.search_dense([1.0, 0.0, 0.0], limit=10)
    assert [chunk.chunk_id for chunk in remaining] == ["doc_a_old"]


def test_qdrant_store_logs_cross_document_near_duplicates() -> None:
    store = QdrantStore(collection_name="unit_dense_cross_doc", backend="memory")
    source = _chunk(
        chunk_id="doc_a_0",
        doc_id="doc_a",
        version="v1",
        chunk_index=0,
        embedding=[1.0, 0.0, 0.0],
    )
    candidate = _chunk(
        chunk_id="doc_b_0",
        doc_id="doc_b",
        version="v1",
        chunk_index=0,
        embedding=[0.9999, 0.0001, 0.0],
    )

    store.upsert_chunks([source])
    store.upsert_chunks([candidate])

    decisions = store.vector_deduplicator.last_report.decisions
    assert decisions[0].decision == "cross_document_match"
    assert decisions[0].matched_chunk_id == "doc_a_0"
