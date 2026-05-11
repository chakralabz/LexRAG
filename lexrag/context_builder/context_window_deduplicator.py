"""Deduplicate context candidates before prompt assembly."""

from __future__ import annotations

from difflib import SequenceMatcher

from lexrag.context_builder.schemas import ContextBuilderConfig, ContextSource


class ContextWindowDeduplicator:
    """Remove redundant sources while preserving provenance.

    The architecture calls for two suppression policies inside the context
    window:

    1. near-identical chunk text should not consume scarce prompt budget twice
    2. chunks covering essentially the same source blocks should collapse to one

    The deduplicator keeps the first surviving source in stable input order so
    citation IDs and downstream audits remain predictable.
    """

    def __init__(self, *, config: ContextBuilderConfig | None = None) -> None:
        self.config = config or ContextBuilderConfig()

    def deduplicate(self, sources: list[ContextSource]) -> list[ContextSource]:
        """Return stable, non-redundant sources."""

        unique: list[ContextSource] = []
        for candidate in sources:
            if self._is_redundant(candidate=candidate, existing=unique):
                continue
            unique.append(candidate)
        return unique

    def _is_redundant(
        self,
        *,
        candidate: ContextSource,
        existing: list[ContextSource],
    ) -> bool:
        """Check whether the candidate adds materially new information."""

        for current in existing:
            if self._same_chunk(candidate=candidate, current=current):
                return True
            if self._same_block_family(candidate=candidate, current=current):
                return True
            if self._near_duplicate_text(candidate=candidate, current=current):
                return True
        return False

    def _same_chunk(
        self,
        *,
        candidate: ContextSource,
        current: ContextSource,
    ) -> bool:
        """Treat identical chunk IDs as duplicates even across retries."""

        return candidate.chunk.chunk_id == current.chunk.chunk_id

    def _same_block_family(
        self,
        *,
        candidate: ContextSource,
        current: ContextSource,
    ) -> bool:
        """Collapse sources that overlap on almost all original blocks."""

        candidate_blocks = set(candidate.citation.source_block_ids)
        current_blocks = set(current.citation.source_block_ids)
        if not candidate_blocks or not current_blocks:
            return False
        overlap = len(candidate_blocks & current_blocks)
        smallest = min(len(candidate_blocks), len(current_blocks))
        return (overlap / smallest) >= self.config.block_overlap_threshold

    def _near_duplicate_text(
        self,
        *,
        candidate: ContextSource,
        current: ContextSource,
    ) -> bool:
        """Use a cheap lexical ratio to suppress near-identical passages."""

        score = SequenceMatcher(None, candidate.chunk.text, current.chunk.text).ratio()
        return score >= self.config.near_duplicate_similarity_threshold
