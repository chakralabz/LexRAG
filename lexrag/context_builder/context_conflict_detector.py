"""Detect obviously conflicting evidence inside one context window."""

from __future__ import annotations

import re

from lexrag.context_builder.schemas import ContextBuilderConfig, ContextSource

_DATE_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
_MONEY_PATTERN = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")
_PERCENT_PATTERN = re.compile(r"\b\d+(?:\.\d+)?%")


class ContextConflictDetector:
    """Surface contradictions that the generator should not silently smooth over.

    This detector is intentionally heuristic rather than semantic. Its job is
    not to prove contradiction; it is to warn the generation layer whenever the
    prompt includes visibly divergent structured facts such as dates, amounts,
    or percentages.
    """

    def __init__(self, *, config: ContextBuilderConfig | None = None) -> None:
        self.config = config or ContextBuilderConfig()

    def detect(self, sources: list[ContextSource]) -> list[str]:
        """Return human-readable conflict warnings for the prompt and logs."""

        warnings: list[str] = []
        for label, pattern in self._patterns().items():
            values = self._distinct_values(sources=sources, pattern=pattern)
            if len(values) >= self.config.conflict_value_count_threshold:
                warnings.append(self._warning(label=label, values=values))
        return warnings

    def _patterns(self) -> dict[str, re.Pattern[str]]:
        """Provide the structured signals that tend to cause legal conflicts."""

        return {
            "dates": _DATE_PATTERN,
            "amounts": _MONEY_PATTERN,
            "percentages": _PERCENT_PATTERN,
        }

    def _distinct_values(
        self,
        *,
        sources: list[ContextSource],
        pattern: re.Pattern[str],
    ) -> list[str]:
        """Collect stable unique values in first-seen order."""

        values: list[str] = []
        seen: set[str] = set()
        for source in sources:
            for match in pattern.findall(source.chunk.text):
                if match in seen:
                    continue
                seen.add(match)
                values.append(match)
        return values

    def _warning(self, *, label: str, values: list[str]) -> str:
        """Create a concise operator- and model-friendly warning string."""

        sample = ", ".join(values[: self.config.conflict_warning_sample_size])
        return f"Potential conflict across {label}: {sample}"
