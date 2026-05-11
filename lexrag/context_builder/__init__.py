"""Production context-builder package.

This package owns Architecture Section 16: transforming citation-resolved,
reranked chunks into a compact, deterministic, generation-ready context window.
It does not retrieve documents, resolve citations, or generate answers.
"""

from lexrag.context_builder.context_conflict_detector import ContextConflictDetector
from lexrag.context_builder.context_prompt_formatter import ContextPromptFormatter
from lexrag.context_builder.context_window_compressor import ContextWindowCompressor
from lexrag.context_builder.context_window_deduplicator import ContextWindowDeduplicator
from lexrag.context_builder.context_window_orderer import ContextWindowOrderer
from lexrag.context_builder.llm_context_builder import LLMContextBuilder
from lexrag.context_builder.schemas import ContextSource, ContextWindow

__all__ = [
    "ContextConflictDetector",
    "ContextPromptFormatter",
    "ContextSource",
    "ContextWindow",
    "ContextWindowCompressor",
    "ContextWindowDeduplicator",
    "ContextWindowOrderer",
    "LLMContextBuilder",
]
