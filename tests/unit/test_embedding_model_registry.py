from __future__ import annotations

from lexrag.ingestion.embeddings.embedding_model_preloader import (
    EmbeddingModelPreloader,
)
from lexrag.ingestion.embeddings.shared_model_registry import SharedModelRegistry


def test_shared_model_registry_caches_tokenizer_instances(monkeypatch) -> None:
    registry = SharedModelRegistry()
    calls: list[tuple[str, bool]] = []

    def fake_load_tokenizer(*, model_name: str, local_files_only: bool) -> object:
        calls.append((model_name, local_files_only))
        return {"model_name": model_name, "local_files_only": local_files_only}

    monkeypatch.setattr(registry, "_load_tokenizer", fake_load_tokenizer)

    first = registry.get_tokenizer(model_name="BAAI/bge-m3", local_files_only=True)
    second = registry.get_tokenizer(model_name="BAAI/bge-m3", local_files_only=True)

    assert first is second
    assert calls == [("BAAI/bge-m3", True)]


def test_embedding_model_preloader_warms_both_artifacts(monkeypatch) -> None:
    registry = SharedModelRegistry()
    preloader = EmbeddingModelPreloader(registry=registry)
    tokenizer_calls: list[tuple[str, bool]] = []
    model_calls: list[tuple[str, bool]] = []

    def fake_load_tokenizer(*, model_name: str, local_files_only: bool) -> object:
        tokenizer_calls.append((model_name, local_files_only))
        return {"tokenizer": model_name}

    def fake_load_model(*, model_name: str, local_files_only: bool) -> object:
        model_calls.append((model_name, local_files_only))
        return {"model": model_name}

    monkeypatch.setattr(registry, "_load_tokenizer", fake_load_tokenizer)
    monkeypatch.setattr(registry, "_load_sentence_transformer", fake_load_model)

    preloader.preload_embedding_stack(
        model_name="BAAI/bge-m3",
        allow_download=False,
    )

    assert tokenizer_calls == [("BAAI/bge-m3", True)]
    assert model_calls == [("BAAI/bge-m3", True)]
