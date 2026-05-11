"""Production generation package.

This package owns Architecture Section 17: prompt assembly, model invocation,
and post-generation safety validation. It consumes context windows and citation
contracts but does not perform retrieval or source resolution itself.
"""

from lexrag.generation.answer_abstention_detector import AnswerAbstentionDetector
from lexrag.generation.answer_generator import AnswerGenerator
from lexrag.generation.answer_validator import AnswerValidator
from lexrag.generation.llm_backend import LLMBackend
from lexrag.generation.pii_detector import PIIDetector
from lexrag.generation.prompt_assembler import PromptAssembler
from lexrag.generation.schemas import (
    GenerationConfig,
    GenerationRequest,
    GenerationResponse,
    GenerationValidation,
    PIIFinding,
)

__all__ = [
    "AnswerAbstentionDetector",
    "AnswerGenerator",
    "AnswerValidator",
    "GenerationConfig",
    "GenerationRequest",
    "GenerationResponse",
    "GenerationValidation",
    "LLMBackend",
    "PIIDetector",
    "PIIFinding",
    "PromptAssembler",
]
