"""Deterministic multi-hop query decomposition heuristics."""

from __future__ import annotations

import re

from lexrag.retrieval.schemas import QueryDecomposerConfig
from lexrag.utils.text import TextNormalizer

_COMPARISON_MARKERS = (
    "compare",
    "difference",
    "differences",
    "versus",
    "vs",
    "between",
    "relationship",
)
_SPLIT_PATTERN = re.compile(r"\b(?:and|vs\.?|versus|between|compared with)\b", re.I)


class QueryDecomposer:
    """Identify likely multi-hop queries and split them into sub-queries.

    The implementation is intentionally deterministic and dependency-light so it
    can serve as a production-safe baseline before an LLM-assisted decomposer is
    introduced. Heuristics are explicit, auditable, and easy to tune.
    """

    def __init__(self, *, config: QueryDecomposerConfig | None = None) -> None:
        self.config = config or QueryDecomposerConfig()
        self.normalizer = TextNormalizer()

    def is_multihop(self, question: str) -> bool:
        """Return whether the question likely needs multiple retrieval hops."""

        normalized = question.strip().lower()
        if not normalized:
            return False
        terms = self.normalizer.tokenize_words(normalized)
        if len(terms) < self.config.min_terms_for_multihop:
            return False
        return self._contains_multihop_signal(normalized=normalized)

    def decompose(self, question: str) -> list[str]:
        """Split a multi-hop question into deterministic sub-queries."""

        normalized = question.strip()
        if not normalized:
            return []
        if not self.is_multihop(normalized):
            return [normalized]
        fragments = self._split_fragments(question=normalized)
        sub_queries = self._deduplicate_preserving_order(fragments)
        return sub_queries[: self.config.max_sub_queries]

    def _contains_multihop_signal(self, *, normalized: str) -> bool:
        """Check for conjunction or comparison markers in the question."""

        if any(marker in normalized for marker in _COMPARISON_MARKERS):
            return True
        return " and " in normalized and "?" not in normalized[:4]

    def _split_fragments(self, *, question: str) -> list[str]:
        """Split the question and retain the shared subject when possible."""

        fragments = [part.strip(" ,;:.") for part in _SPLIT_PATTERN.split(question)]
        fragments = [fragment for fragment in fragments if fragment]
        if len(fragments) <= 1:
            return [question]
        prefix = self._shared_prefix(question=question)
        return [
            self._compose_fragment(prefix=prefix, fragment=fragment)
            for fragment in fragments
        ]

    def _shared_prefix(self, *, question: str) -> str:
        """Extract the stable intent prefix that should lead each fragment."""

        lowered = question.lower()
        for marker in _COMPARISON_MARKERS:
            index = lowered.find(marker)
            if index >= 0:
                return question[: index + len(marker)].strip(" ,;:.")
        return ""

    def _compose_fragment(self, *, prefix: str, fragment: str) -> str:
        """Attach the shared prefix to a split fragment when useful."""

        if not prefix:
            return fragment
        if fragment.lower().startswith(prefix.lower()):
            return fragment
        return f"{prefix} {fragment}".strip()

    def _deduplicate_preserving_order(self, fragments: list[str]) -> list[str]:
        """Drop duplicate fragments while keeping deterministic ordering."""

        seen: set[str] = set()
        ordered: list[str] = []
        for fragment in fragments:
            key = fragment.lower()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(fragment)
        return ordered
