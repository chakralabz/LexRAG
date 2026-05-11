"""Detect explicit abstentions in generated answers."""

from __future__ import annotations

from lexrag.generation.schemas import GenerationConfig


class AnswerAbstentionDetector:
    """Detect whether the model declined to answer from the provided sources."""

    def __init__(self, *, config: GenerationConfig | None = None) -> None:
        self.config = config or GenerationConfig()

    def is_abstention(self, answer_text: str) -> bool:
        """Return true when the answer clearly signals non-answer behavior."""

        normalized = answer_text.lower()
        return any(phrase in normalized for phrase in self.config.abstention_phrases)
