"""Deterministic citation identifier allocation."""

from __future__ import annotations


class CitationIdSequence:
    """Allocate stable one-based citation identifiers.

    The architecture assumes the context builder will present sources in a
    deterministic order and the generation layer will reference them by inline
    numeric IDs. This class keeps that policy explicit and easy to swap if the
    formatting convention evolves later.
    """

    def __init__(self, *, start: int = 1) -> None:
        if start <= 0:
            raise ValueError("start must be positive")
        self._next_id = start

    def next_id(self) -> int:
        """Return the next citation identifier in sequence."""

        citation_id = self._next_id
        self._next_id += 1
        return citation_id
