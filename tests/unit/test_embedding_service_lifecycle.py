from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from lexrag.indexing.schemas import Chunk, ChunkMetadata
from lexrag.services.embedding_service import EmbeddingService


def test_embedding_service_loads_generator_once() -> None:
    calls: list[str] = []

    def generator_factory() -> Any:
        calls.append("load")
        return SimpleNamespace(
            backend=SimpleNamespace(model_name="fake", model_version="v1"),
            embed_texts=lambda texts: [[1.0] for _ in texts],
            embed_query=lambda query: [float(len(query))],
            embed_chunks=lambda chunks: chunks,
        )

    service = EmbeddingService(generator_factory=generator_factory)

    service.load()
    vector = service.embed_query("contract")
    service.embed_texts(["a", "b"])

    assert vector == [8.0]
    assert calls == ["load"]


def test_embedding_service_embeds_prepared_chunks() -> None:
    chunk = Chunk(
        chunk_id="doc_chunk_1",
        text="body",
        embedding_text="prepared",
        metadata=ChunkMetadata(chunk_index=0, total_chunks=1),
    )
    generator = SimpleNamespace(
        backend=SimpleNamespace(model_name="fake", model_version="v1"),
        embed_texts=lambda texts: [[0.5] for _ in texts],
    )
    service = EmbeddingService(generator_factory=lambda: cast(Any, generator))

    embedded = service.embed_prepared_chunks([chunk])

    assert embedded[0].embedding == [0.5]
    assert embedded[0].metadata.embedding_model == "fake"
