"""Backend contract for answer generation models."""

from __future__ import annotations

from typing import Protocol


class LLMBackend(Protocol):
    """Minimal interface required by the production generation orchestrator."""

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Generate one complete answer string for the supplied prompts."""
