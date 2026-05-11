from __future__ import annotations

from pathlib import Path

import pytest

from lexrag.ingestion.file_ingestion import FileIngestionConfig, FileLoaderPipeline


def test_loader_returns_ready_result_for_valid_file(tmp_path: Path) -> None:
    path = tmp_path / "policy.txt"
    path.write_text("plain text", encoding="utf-8")

    result = FileLoaderPipeline().load_file(path)

    assert result.is_ready is True
    assert result.rejection_reason is None
    assert result.ingestion_report.detection.document_family == "text"


def test_loader_blocks_paths_outside_allowed_roots(tmp_path: Path) -> None:
    allowed_root = tmp_path / "allowed"
    blocked_root = tmp_path / "blocked"
    allowed_root.mkdir()
    blocked_root.mkdir()
    blocked = blocked_root / "note.txt"
    blocked.write_text("outside root", encoding="utf-8")
    loader = FileLoaderPipeline(
        config=FileIngestionConfig(allowed_root_paths=(str(allowed_root),))
    )

    with pytest.raises(PermissionError, match="outside the configured roots"):
        loader.load_file(blocked)


def test_loader_blocks_symlink_when_following_is_disabled(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("linked file", encoding="utf-8")
    link = tmp_path / "target-link.txt"
    link.symlink_to(target)

    with pytest.raises(PermissionError, match="Symlinked paths are not allowed"):
        FileLoaderPipeline().load_file(link)


def test_loader_expands_directory_and_marks_batch_duplicates(tmp_path: Path) -> None:
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("same content", encoding="utf-8")
    second.write_text("same content", encoding="utf-8")

    results = FileLoaderPipeline().load_path(tmp_path)

    assert len(results) == 2
    assert results[0].is_ready is True
    assert results[1].is_ready is False
    assert results[1].rejection_reason == "duplicate_file_in_batch"
