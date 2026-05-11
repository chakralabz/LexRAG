from __future__ import annotations

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.schemas.chunk_metadata import ChunkMetadata
from lexrag.ingestion.embeddings import (
    EmbeddingPreparationConfig,
    EmbeddingPreparationService,
)


def _metadata(*, chunk_type: str = "paragraph") -> ChunkMetadata:
    return ChunkMetadata(
        doc_id="doc_1",
        chunk_index=0,
        total_chunks=1,
        page_start=1,
        page_end=1,
        section_title="Definitions",
        section_path=["Part I", "Definitions"],
        heading_anchor="Definitions",
        chunk_type=chunk_type,
        chunking_strategy="semantic_merge",
        token_count=5,
    )


def test_embedding_preparation_adds_heading_context_for_paragraphs() -> None:
    service = EmbeddingPreparationService()
    chunk = Chunk(
        chunk_id="doc_1_chunk_1",
        text="A regulated entity must retain records.",
        metadata=_metadata(),
    )

    prepared = service.prepare_chunk(chunk=chunk)

    assert prepared.embedding_text == (
        "[HEADING: Definitions] A regulated entity must retain records."
    )
    assert prepared.metadata.metadata["embedding_text_truncated"] is False


def test_embedding_preparation_serializes_tables() -> None:
    service = EmbeddingPreparationService()
    chunk = Chunk(
        chunk_id="doc_1_chunk_2",
        text="| Revenue | 2025 |\n| 100 | 200 |",
        metadata=_metadata(chunk_type="table"),
    )

    prepared = service.prepare_chunk(chunk=chunk)

    assert prepared.embedding_text is not None
    assert prepared.embedding_text.startswith("[TABLE: Definitions]")
    assert "Revenue ; 2025" in prepared.embedding_text


def test_embedding_preparation_truncates_over_budget_text() -> None:
    service = EmbeddingPreparationService(
        config=EmbeddingPreparationConfig(max_embedding_tokens=4)
    )
    chunk = Chunk(
        chunk_id="doc_1_chunk_3",
        text="alpha beta gamma delta epsilon zeta",
        metadata=_metadata(),
    )

    prepared = service.prepare_chunk(chunk=chunk)

    assert prepared.metadata.metadata["embedding_text_truncated"] is True
    assert prepared.metadata.metadata["embedding_text_token_count"] == 4
