"""Trim context windows without discarding critical evidence."""

from __future__ import annotations

from lexrag.context_builder.schemas import ContextBuilderConfig, ContextSource
from lexrag.utils.text import TextNormalizer


class ContextWindowCompressor:
    """Keep context within budget while preserving query coverage.

    The architecture explicitly forbids naive tail trimming. This compressor
    removes the weakest sources first, but protects any source that is the sole
    support for at least one query term so recall does not collapse silently.
    """

    def __init__(self, *, config: ContextBuilderConfig | None = None) -> None:
        self.config = config or ContextBuilderConfig()
        self.normalizer = TextNormalizer()

    def compress(
        self,
        *,
        query: str,
        sources: list[ContextSource],
    ) -> list[ContextSource]:
        """Trim sources until the total token budget is satisfied."""

        kept = list(sources)
        while self._token_total(kept) > self.config.max_context_tokens:
            removable = self._removable_sources(query=query, sources=kept)
            if not removable:
                break
            kept.remove(removable[0])
        return kept

    def _removable_sources(
        self,
        *,
        query: str,
        sources: list[ContextSource],
    ) -> list[ContextSource]:
        """Rank removable sources from weakest to strongest."""

        return sorted(
            (
                source
                for source in sources
                if not self._sole_support(source=source, query=query, sources=sources)
            ),
            key=self._removal_key,
        )

    def _removal_key(self, source: ContextSource) -> tuple[float, float, int]:
        """Prefer dropping lower-quality, lower-ranked, later-added evidence."""

        return (source.quality_score, source.rank_score, -source.citation.citation_id)

    def _sole_support(
        self,
        *,
        source: ContextSource,
        query: str,
        sources: list[ContextSource],
    ) -> bool:
        """Protect sources that uniquely cover a query term."""

        query_terms = self.normalizer.token_set_words(query)
        source_terms = self.normalizer.token_set_words(source.chunk.text)
        for term in query_terms & source_terms:
            if self._support_count(term=term, sources=sources) == 1:
                return True
        return False

    def _support_count(self, *, term: str, sources: list[ContextSource]) -> int:
        """Count how many sources contain a given normalized query term."""

        return sum(
            term in self.normalizer.token_set_words(item.chunk.text) for item in sources
        )

    def _token_total(self, sources: list[ContextSource]) -> int:
        """Compute the current prompt token estimate."""

        return sum(source.token_count for source in sources)
