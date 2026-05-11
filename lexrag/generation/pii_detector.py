"""Lightweight PII scanning for generated answers."""

from __future__ import annotations

import re

from lexrag.generation.schemas import GenerationConfig, PIIFinding


class PIIDetector:
    """Scan generated text for high-risk PII patterns before release."""

    def __init__(self, *, config: GenerationConfig | None = None) -> None:
        self.config = config or GenerationConfig()

    def detect(self, text: str) -> list[PIIFinding]:
        """Return structured PII findings in first-seen order."""

        findings: list[PIIFinding] = []
        for label, pattern in self._patterns().items():
            findings.extend(self._find_matches(text=text, label=label, pattern=pattern))
        return findings

    def _patterns(self) -> dict[str, re.Pattern[str]]:
        """Define the small, auditable PII surface enforced by default."""

        return {
            "email": re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
            "phone": re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b"),
        }

    def _find_matches(
        self,
        *,
        text: str,
        label: str,
        pattern: re.Pattern[str],
    ) -> list[PIIFinding]:
        """Convert regex matches into stable schema objects."""

        return [
            PIIFinding(
                kind=label,
                match=match.group(0),
                start=match.start(),
                end=match.end(),
            )
            for match in pattern.finditer(text)
        ]
