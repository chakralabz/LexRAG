"""Deterministic ordering for prompt context sources."""

from __future__ import annotations

from lexrag.context_builder.schemas import ContextBuilderConfig, ContextSource


class ContextWindowOrderer:
    """Order sources for high signal and predictable citation behavior.

    The architecture asks for document grouping, section-aware ordering, and
    score-sensitive prioritization. This class makes that policy explicit and
    isolated so alternative ordering strategies can be swapped safely later.
    """

    def __init__(self, *, config: ContextBuilderConfig | None = None) -> None:
        self.config = config or ContextBuilderConfig()

    def order(self, sources: list[ContextSource]) -> list[ContextSource]:
        """Return deterministically ordered sources."""

        return sorted(sources, key=self._sort_key)

    def _sort_key(self, source: ContextSource) -> tuple[float, str, int, str, int]:
        """Prioritize stronger evidence while keeping order stable within docs."""

        return (
            -source.rank_score,
            source.citation.document_id or "",
            source.citation.page,
            source.citation.section or "",
            source.citation.citation_id,
        )
