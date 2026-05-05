"""Lightweight HTML text extraction helpers.

The parsing package keeps HTML extraction dependency-light so the fallback path
stays available in constrained environments such as CI and local smoke tests.
"""

from __future__ import annotations

from html.parser import HTMLParser


class HtmlTextExtractor(HTMLParser):
    """Extract readable text from HTML while ignoring markup.

    The goal is not perfect DOM fidelity. The goal is deterministic, low-risk
    fallback extraction that produces clean text for downstream normalization.
    """

    def __init__(self) -> None:
        """Initialize the accumulator used during HTML parsing."""
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        """Store meaningful text fragments from the HTML stream.

        Args:
            data: Raw text payload emitted by ``HTMLParser``.
        """
        text = data.strip()
        if text:
            self._parts.append(text)

    def text(self) -> str:
        """Return the normalized visible text content."""
        return " ".join(self._parts).strip()


TextExtractor = HtmlTextExtractor
