"""Inline citation parsing utilities."""

from __future__ import annotations

import re

from lexrag.citation.schemas import CitationReference


class CitationReferenceParser:
    """Extract inline citation references from generated answer text.

    The parser intentionally accepts only the numeric citation contract that the
    architecture prescribes: ``[1]``, ``[1, 2]``, or ``[SOURCE 3]``. Keeping
    this narrow prevents downstream validators from silently normalizing ad hoc
    formats that the prompt never asked the model to emit.
    """

    _REFERENCE_PATTERN = re.compile(
        r"\[(?:SOURCE\s+)?(?P<body>\d+(?:\s*,\s*\d+)*)\]",
        re.IGNORECASE,
    )

    def parse(self, text: str) -> list[CitationReference]:
        """Return ordered citation references discovered in ``text``."""

        references: list[CitationReference] = []
        for match in self._REFERENCE_PATTERN.finditer(text):
            references.extend(self._expand_match(match=match))
        return references

    def _expand_match(self, *, match: re.Match[str]) -> list[CitationReference]:
        """Expand grouped references such as ``[1, 2]`` into atomic records."""

        body = match.group("body")
        start_index = match.start()
        end_index = match.end()
        return [
            CitationReference(
                citation_id=int(token.strip()),
                raw_text=match.group(0),
                start_index=start_index,
                end_index=end_index,
            )
            for token in body.split(",")
        ]
