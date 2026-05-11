"""Collect deterministic file candidates for directory-style ingestion."""

from __future__ import annotations

from pathlib import Path

from lexrag.ingestion.file_ingestion.schemas.file_ingestion_config import (
    FileIngestionConfig,
)


class BatchFileCollector:
    """Expand directories into a sorted list of file ingestion candidates."""

    def __init__(self, config: FileIngestionConfig | None = None) -> None:
        """Store batching policy for later directory expansion.

        Args:
            config: Optional shared ingestion configuration.
        """
        self.config = config or FileIngestionConfig()

    def collect(self, *, path: Path, recursive: bool) -> list[Path]:
        """Return concrete file or symlink candidates under a directory.

        Args:
            path: Resolved directory path to expand.
            recursive: Whether nested children should be included.

        Returns:
            Sorted candidate paths ready for loader processing.
        """
        candidates = self._sorted_candidates(path=path, recursive=recursive)
        self._assert_not_empty(path=path, candidates=candidates)
        self._assert_batch_limit(candidates=candidates)
        return candidates

    def _sorted_candidates(self, *, path: Path, recursive: bool) -> list[Path]:
        """Build a deterministic candidate list for stable downstream results.

        Args:
            path: Resolved directory path to expand.
            recursive: Whether nested children should be included.

        Returns:
            Sorted list of concrete file and symlink candidates.
        """
        iterator = path.rglob("*") if recursive else path.iterdir()
        return sorted(item for item in iterator if item.is_file() or item.is_symlink())

    def _assert_not_empty(self, *, path: Path, candidates: list[Path]) -> None:
        """Reject empty directories with an actionable error.

        Args:
            path: Resolved directory path that was expanded.
            candidates: Candidate list produced from the directory.
        """
        if candidates:
            return
        raise FileNotFoundError(f"No files were found under path: {path}")

    def _assert_batch_limit(self, *, candidates: list[Path]) -> None:
        """Prevent unexpectedly large expansions from one caller request.

        Args:
            candidates: Candidate list produced from directory expansion.
        """
        if len(candidates) <= self.config.max_batch_files:
            return
        raise ValueError("batch_limit_exceeded")
