"""Shared stage contract for block normalization.

Every normalization stage receives one immutable ``ParsedBlock`` and returns a
new immutable ``ParsedBlock``. Stages may keep document-scoped state, but that
state must be reset between documents by the orchestrator.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from lexrag.ingestion.normalizer.schemas import BlockNormalizationConfig
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class BaseNormalizer(ABC):
    """Base class for all normalization stages.

    Args:
        config: Immutable normalization settings shared across the pipeline.
    """

    def __init__(self, config: BlockNormalizationConfig) -> None:
        self.config = config

    @abstractmethod
    def normalize(self, block: ParsedBlock) -> ParsedBlock:
        """Transforms one parsed block deterministically.

        Args:
            block: Canonical parser output block.

        Returns:
            A new normalized block instance.
        """

    def should_drop(self, block: ParsedBlock) -> bool:
        """Returns whether the stage wants the block removed from the stream.

        Args:
            block: Candidate normalized block.

        Returns:
            ``True`` when the block should be removed from further processing.
        """
        return False

    def reset(self) -> None:
        """Clears document-scoped state before a new document batch begins."""
        return
