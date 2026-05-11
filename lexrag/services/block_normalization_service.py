"""Public block normalization service."""

from __future__ import annotations

from lexrag.ingestion.normalizer import BlockNormalizer
from lexrag.ingestion.parser import ParsedBlock


class BlockNormalizationService:
    """Normalize parsed blocks into the package's canonical form."""

    def __init__(self, *, normalizer: BlockNormalizer | None = None) -> None:
        self._normalizer = normalizer or BlockNormalizer()

    def normalize(self, blocks: list[ParsedBlock]) -> list[ParsedBlock]:
        """Normalize a parsed document block sequence."""
        return self._normalizer.normalize(blocks)
