"""Public API for the block-normalization layer.

The normalization package is the boundary between parser output and the rest of
the ingestion pipeline. Everything exported here is intentionally small and
stable so downstream modules can depend on the package without pulling in the
implementation details of individual stages.
"""

from lexrag.ingestion.normalizer.base_normalizer import BaseNormalizer
from lexrag.ingestion.normalizer.block_normalizer import BlockNormalizer
from lexrag.ingestion.normalizer.code_block_normalizer import CodeBlockNormalizer
from lexrag.ingestion.normalizer.heading_normalizer import HeadingNormalizer
from lexrag.ingestion.normalizer.metadata_enricher import MetadataEnricher
from lexrag.ingestion.normalizer.ocr_normalizer import OCRNormalizer
from lexrag.ingestion.normalizer.ocr_policy_normalizer import OCRPolicyNormalizer
from lexrag.ingestion.normalizer.parser_artifact_cleaner import ParserArtifactCleaner
from lexrag.ingestion.normalizer.schemas import (
    BlockNormalizationConfig,
    build_block_normalization_config,
)
from lexrag.ingestion.normalizer.section_path_normalizer import SectionPathNormalizer
from lexrag.ingestion.normalizer.table_normalizer import TableNormalizer
from lexrag.ingestion.normalizer.text_normalizer import TextNormalizer

__all__ = [
    "BaseNormalizer",
    "BlockNormalizationConfig",
    "BlockNormalizer",
    "CodeBlockNormalizer",
    "HeadingNormalizer",
    "MetadataEnricher",
    "OCRNormalizer",
    "OCRPolicyNormalizer",
    "ParserArtifactCleaner",
    "SectionPathNormalizer",
    "TableNormalizer",
    "TextNormalizer",
    "build_block_normalization_config",
]
