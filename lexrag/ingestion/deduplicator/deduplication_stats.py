"""Deduplication run statistics model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeduplicationStats:
    """Simple operational counters for deduplication runs."""

    total_seen: int
    total_skipped: int

    @property
    def skip_ratio(self) -> float:
        """Returns fraction of skipped chunks in the last deduplication run."""
        if self.total_seen == 0:
            return 0.0
        return self.total_skipped / self.total_seen
