"""Prompt assembly for grounded answer generation."""

from __future__ import annotations

from lexrag.generation.schemas import GenerationConfig, GenerationRequest


class PromptAssembler:
    """Build system and user prompts that enforce grounding behavior."""

    def __init__(self, *, config: GenerationConfig | None = None) -> None:
        self.config = config or GenerationConfig()

    def build(self, request: GenerationRequest) -> tuple[str, str]:
        """Return the system and user prompts for one generation request."""

        return (self._system_prompt(request), self._user_prompt(request))

    def _system_prompt(self, request: GenerationRequest) -> str:
        """Encode the non-negotiable answer policy in one stable prompt."""

        lines = [
            self.config.system_role_prompt,
            "Always cite supporting sources using [N] inline notation.",
            "If the answer is not supported by the provided sources, abstain clearly.",
            "If the provided sources conflict, surface the conflict instead of guessing.",
        ]
        if request.context_window.conflict_detected:
            lines.append(
                "Conflict warning is present in the context. Address it directly."
            )
        return "\n".join(lines)

    def _user_prompt(self, request: GenerationRequest) -> str:
        """Embed the user question alongside the curated context window."""

        return (
            f"Question:\n{request.question}\n\n"
            f"Context:\n{request.context_window.formatted_context}\n\n"
            "Answer with grounded claims only."
        )
