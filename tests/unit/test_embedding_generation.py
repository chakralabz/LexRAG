from __future__ import annotations

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.schemas.chunk_metadata import ChunkMetadata
from lexrag.ingestion.embeddings import (
    EmbeddingGenerationConfig,
    EmbeddingGenerator,
)
from lexrag.ingestion.embeddings.deterministic_hash_embedding_backend import (
    DeterministicHashEmbeddingBackend,
)


def _chunk(*, text: str) -> Chunk:
    metadata = ChunkMetadata(
        doc_id="doc_1",
        chunk_index=0,
        total_chunks=1,
        page_start=1,
        page_end=1,
        section_title="Overview",
        section_path=["Overview"],
        chunk_type="paragraph",
        chunking_strategy="semantic_merge",
        token_count=3,
    )
    return Chunk(chunk_id="doc_1_chunk_1", text=text, metadata=metadata)


def test_embedding_generator_populates_embedding_text_and_metadata() -> None:
    backend = DeterministicHashEmbeddingBackend(dimension=16)
    generator = EmbeddingGenerator(
        backend=backend,
        config=EmbeddingGenerationConfig(
            model_name=backend.model_name,
            model_version=backend.model_version,
            expected_dimension=16,
            batch_size=4,
        ),
    )

    embedded = generator.embed_chunks([_chunk(text="regulatory capital buffer")])[0]

    assert embedded.embedding is not None
    assert len(embedded.embedding) == 16
    assert embedded.embedding_text is not None
    assert embedded.metadata.embedding_model == "deterministic-hash"
    assert embedded.metadata.embedding_model_version == "v1"


def test_embedding_generator_caches_duplicate_payloads() -> None:
    backend = DeterministicHashEmbeddingBackend(dimension=8)
    generator = EmbeddingGenerator(
        backend=backend,
        config=EmbeddingGenerationConfig(
            model_name=backend.model_name,
            model_version=backend.model_version,
            expected_dimension=8,
            batch_size=2,
        ),
    )

    vectors = generator.embed_texts(["same payload", "same payload"])

    assert len(vectors) == 2
    assert vectors[0] == vectors[1]
