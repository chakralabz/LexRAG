"""Streaming file hashing utilities for ingestion.

Hashing is used both for auditability and for multi-file duplicate detection.
The implementation streams from disk so large files do not need to be loaded
fully into memory.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


class FileHashCalculator:
    """Compute stable file digests for deduplication and audit trails."""

    def __init__(self, *, chunk_size_bytes: int = 1024 * 1024) -> None:
        """Initialize the hash calculator.

        Args:
            chunk_size_bytes: Read size used while streaming the file.
        """
        self.chunk_size_bytes = chunk_size_bytes

    def sha256(self, path: Path) -> str:
        """Compute the SHA-256 digest for a file.

        Args:
            path: File path to hash.

        Returns:
            Lowercase hexadecimal SHA-256 digest.
        """
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(self.chunk_size_bytes), b""):
                digest.update(chunk)
        return digest.hexdigest()
