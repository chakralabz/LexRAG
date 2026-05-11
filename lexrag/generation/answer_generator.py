"""Top-level generation orchestrator."""

from __future__ import annotations

from lexrag.generation.answer_validator import AnswerValidator
from lexrag.generation.llm_backend import LLMBackend
from lexrag.generation.prompt_assembler import PromptAssembler
from lexrag.generation.schemas import (
    GenerationConfig,
    GenerationRequest,
    GenerationResponse,
)


class AnswerGenerator:
    """Generate grounded answers from context windows and validate the result."""

    def __init__(
        self,
        *,
        backend: LLMBackend,
        config: GenerationConfig | None = None,
        prompt_assembler: PromptAssembler | None = None,
        validator: AnswerValidator | None = None,
    ) -> None:
        self.backend = backend
        self.config = config or GenerationConfig()
        self.prompt_assembler = prompt_assembler or PromptAssembler(config=self.config)
        self.validator = validator or AnswerValidator(config=self.config)

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate one final answer and attach post-generation validation."""

        system_prompt, user_prompt = self.prompt_assembler.build(request)
        answer_text = self.backend.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=self.config.max_answer_tokens,
            temperature=self.config.temperature,
        ).strip()
        validation = self.validator.validate(
            answer_text=answer_text,
            context_window=request.context_window,
        )
        return GenerationResponse(answer_text=answer_text, validation=validation)
