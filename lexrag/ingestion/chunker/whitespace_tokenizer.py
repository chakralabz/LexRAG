"""Whitespace tokenizer fallback for environments without transformers."""

from __future__ import annotations


class WhitespaceTokenizer:
    """Provide minimal tokenizer compatibility with deterministic behavior.

    This fallback is intentionally simple and is used only when the Hugging Face
    `transformers` runtime is unavailable in the current environment.
    """

    is_fast = True

    def tokenize(self, text: str) -> list[str]:
        """Tokenize by splitting on whitespace."""
        return text.split()

    def convert_tokens_to_string(self, tokens: list[str]) -> str:
        """Reconstruct string from whitespace tokens."""
        return " ".join(tokens)
