"""Post-generation safety and grounding validation."""

from __future__ import annotations

from lexrag.citation import CitationResolver
from lexrag.context_builder.schemas import ContextWindow
from lexrag.generation.answer_abstention_detector import AnswerAbstentionDetector
from lexrag.generation.pii_detector import PIIDetector
from lexrag.generation.schemas import GenerationConfig, GenerationValidation


class AnswerValidator:
    """Validate that the generated answer satisfies production safety rules."""

    def __init__(
        self,
        *,
        config: GenerationConfig | None = None,
        citation_resolver: CitationResolver | None = None,
        abstention_detector: AnswerAbstentionDetector | None = None,
        pii_detector: PIIDetector | None = None,
    ) -> None:
        self.config = config or GenerationConfig()
        self.citation_resolver = citation_resolver or CitationResolver()
        self.abstention_detector = abstention_detector or AnswerAbstentionDetector(
            config=self.config
        )
        self.pii_detector = pii_detector or PIIDetector(config=self.config)

    def validate(
        self,
        *,
        answer_text: str,
        context_window: ContextWindow,
    ) -> GenerationValidation:
        """Return a structured validation report for one answer."""

        citation_validation = self.citation_resolver.validate_answer(
            answer_text,
            resolution=context_window.to_citation_resolution(),
        )
        pii_findings = self.pii_detector.detect(answer_text)
        is_abstained = self.abstention_detector.is_abstention(answer_text)
        return GenerationValidation(
            citation_validation=citation_validation,
            pii_findings=pii_findings,
            is_abstained=is_abstained,
            is_valid=citation_validation.is_valid and not pii_findings,
        )
