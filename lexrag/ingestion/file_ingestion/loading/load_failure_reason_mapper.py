"""Translate loader exceptions into stable rejection reason codes."""

from __future__ import annotations


class LoadFailureReasonMapper:
    """Map filesystem and policy failures to structured rejection reasons."""

    def map(self, exc: Exception) -> str:
        """Return a stable reason code for a load-time failure.

        Args:
            exc: Raised exception from the load path.

        Returns:
            Stable rejection reason code for downstream callers.
        """
        message = str(exc).lower()
        if "symlinked" in message:
            return "symlink_not_allowed"
        if "outside the configured roots" in message:
            return "outside_allowed_roots"
        if "does not exist" in message:
            return "file_not_found"
        if "not a file" in message:
            return "not_a_file"
        return exc.__class__.__name__
