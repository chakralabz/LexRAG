from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from lexrag.indexing.schemas import Chunk, ChunkMetadata
from lexrag.pipeline.rag_pipeline import RAGPipeline


def test_pipeline_ingest_composes_services() -> None:
    chunk = Chunk(
        chunk_id="doc_chunk_1",
        text="retrieval text",
        embedding_text="retrieval text",
        metadata=ChunkMetadata(chunk_index=0, total_chunks=1),
    )
    audit_events: list[dict[str, Any]] = []
    pipeline = RAGPipeline(
        file_validation_service=cast(
            Any,
            SimpleNamespace(
                validate_many=lambda paths: [
                    SimpleNamespace(is_valid=True, path=str(paths[0]))
                ]
            ),
        ),
        parser_service=cast(
            Any,
            SimpleNamespace(
                load=lambda: None,
                close=lambda: None,
                parse_document=lambda path: ["parsed", str(path)],
            ),
        ),
        block_normalization_service=cast(
            Any, SimpleNamespace(normalize=lambda blocks: blocks)
        ),
        deduplication_service=cast(
            Any,
            SimpleNamespace(
                deduplicate_blocks=lambda blocks: blocks,
                deduplicate_vectors=lambda chunks: chunks,
            ),
        ),
        chunking_service=cast(Any, SimpleNamespace(chunk=lambda blocks: [chunk])),
        embedding_preparation_service=cast(
            Any, SimpleNamespace(prepare_chunks=lambda chunks: chunks)
        ),
        embedding_service=cast(
            Any,
            SimpleNamespace(
                load=lambda: None,
                close=lambda: None,
                embed_prepared_chunks=lambda chunks: chunks,
                embed_chunks=lambda chunks: chunks,
            ),
        ),
        audit_service=cast(
            Any,
            SimpleNamespace(
                validate_chunks=lambda chunks: [
                    SimpleNamespace(subject_id="doc_chunk_1", passed=True)
                ]
            ),
        ),
        observability_service=cast(
            Any,
            SimpleNamespace(
                configure=lambda: None,
                record_event=lambda event, metadata=None: audit_events.append(
                    {"event": event, "metadata": metadata}
                ),
            ),
        ),
    )

    ingested = pipeline.ingest([Path("/tmp/document.pdf")])

    assert ingested == [chunk]
    assert audit_events == []


def test_pipeline_uses_injected_retriever() -> None:
    chunk = Chunk(
        chunk_id="doc_chunk_1",
        text="retrieval text",
        metadata=ChunkMetadata(chunk_index=0, total_chunks=1),
    )
    retriever = SimpleNamespace(
        retrieve=lambda query, top_k=None, metadata_filters=None: [chunk]
    )
    pipeline = RAGPipeline(retriever=cast(Any, retriever))

    results = pipeline.retrieve("what is the clause?", top_k=3)

    assert results == [chunk]
