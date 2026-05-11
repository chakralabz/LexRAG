"""Text normalization helpers shared across ingestion, retrieval, and scripts."""

from __future__ import annotations

import re

_WORD_TOKEN_PATTERN = re.compile(r"\w+")
_NON_WHITESPACE_PATTERN = re.compile(r"\S+")
_SAFE_ID_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")


class TextNormalizer:
    """Centralized text processing helpers for consistent behavior."""

    def tokenize_words(self, text: str) -> list[str]:
        """Tokenizes text into lowercase word terms."""
        return _WORD_TOKEN_PATTERN.findall(text.lower())

    def tokenize_non_whitespace(self, text: str) -> list[str]:
        """Tokenizes text by non-whitespace spans."""
        return _NON_WHITESPACE_PATTERN.findall(text.strip())

    def token_set_words(self, text: str) -> set[str]:
        """Returns unique lowercase word tokens."""
        return set(self.tokenize_words(text))

    def sanitize_identifier(self, raw: str, *, default: str = "doc") -> str:
        """Sanitizes user/content IDs into a stable safe identifier."""
        cleaned = _SAFE_ID_PATTERN.sub("_", raw).strip("_").lower()
        return cleaned or default

    def truncate_words(self, text: str, *, limit: int) -> str:
        """Returns the first N words from input text."""
        words = [part for part in text.strip().split() if part]
        return " ".join(words[:limit]).strip()
