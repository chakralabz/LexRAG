"""Safe path resolution helpers for file ingestion."""

from __future__ import annotations

from pathlib import Path

from lexrag.ingestion.file_ingestion.schemas.file_ingestion_config import (
    FileIngestionConfig,
)


class FilePathResolver:
    """Resolve caller-provided paths into safe canonical filesystem paths."""

    def __init__(self, config: FileIngestionConfig | None = None) -> None:
        """Store immutable path policy for future resolution calls.

        Args:
            config: Optional shared ingestion configuration.
        """
        self.config = config or FileIngestionConfig()

    def resolve(self, path: str | Path) -> Path:
        """Resolve one path and enforce symlink and root constraints.

        Args:
            path: Caller-provided file or directory path.

        Returns:
            Canonical resolved path that passed the policy checks.
        """
        candidate = Path(path).expanduser()
        self._assert_exists(candidate)
        self._assert_symlink_allowed(candidate)
        resolved = candidate.resolve(strict=True)
        self._assert_allowed_root(resolved)
        return resolved

    def _assert_exists(self, path: Path) -> None:
        """Raise when a candidate path is missing.

        Args:
            path: Candidate path to validate.
        """
        if path.exists():
            return
        raise FileNotFoundError(f"Document does not exist: {path}")

    def _assert_symlink_allowed(self, path: Path) -> None:
        """Raise when a symlink violates the configured policy.

        Args:
            path: Candidate path to validate.
        """
        if not path.is_symlink() or self.config.follow_symlinks:
            return
        raise PermissionError(f"Symlinked paths are not allowed: {path}")

    def _assert_allowed_root(self, path: Path) -> None:
        """Block directory traversal outside explicitly configured roots.

        Args:
            path: Resolved path to validate.
        """
        roots = self._allowed_roots()
        if not roots or any(path.is_relative_to(root) for root in roots):
            return
        raise PermissionError(f"Path is outside the configured roots: {path}")

    def _allowed_roots(self) -> tuple[Path, ...]:
        """Resolve configured root strings once per call for accurate comparisons.

        Returns:
            Tuple of canonical allowed root paths.
        """
        return tuple(
            Path(root).expanduser().resolve() for root in self.config.allowed_root_paths
        )
