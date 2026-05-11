"""Production block-level deduplicator aligned with the architecture doc."""

from __future__ import annotations

import hashlib

from lexrag.ingestion.deduplicator.deduplication_stats import DeduplicationStats
from lexrag.ingestion.deduplicator.deduplicator_base import Deduplicator
from lexrag.ingestion.deduplicator.schemas import (
    BlockDeduplicationConfig,
    BlockDeduplicationDecision,
    DeduplicationRunReport,
)
from lexrag.ingestion.deduplicator.similarity_engine import SimilarityEngine
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock
from lexrag.observability.logging_runtime import get_logger
from lexrag.utils.text import TextNormalizer

logger = get_logger(__name__)


class BlockDeduplicator(Deduplicator):
    """Remove redundant parsed blocks without losing legal provenance.

    The implementation mirrors the architecture's intent rather than chasing
    every possible dedup heuristic in one place. Exact duplicates are removed
    deterministically, near-duplicates are compared via token-set Jaccard, and
    recurring low-value page furniture can be suppressed when it repeats across
    many pages. Legal-sensitive section content is preserved unless the match is
    effectively exact.
    """

    def __init__(
        self,
        *,
        config: BlockDeduplicationConfig | None = None,
        similarity_engine: SimilarityEngine | None = None,
    ) -> None:
        self.config = config or BlockDeduplicationConfig()
        self.similarity_engine = similarity_engine or SimilarityEngine()
        self.text_normalizer = TextNormalizer()
        self.last_stats = DeduplicationStats(total_seen=0, total_skipped=0)
        self.last_report = DeduplicationRunReport()

    def deduplicate(self, blocks: list[ParsedBlock]) -> list[ParsedBlock]:
        """Remove duplicates while preserving input order for kept blocks.

        Args:
            blocks: Normalized parsed blocks from one document stream.

        Returns:
            Blocks that survived deduplication with audit metadata attached.
        """
        recurring = self._repeated_patterns(blocks)
        return self._deduplicate_blocks(blocks=blocks, recurring=recurring)

    def _deduplicate_blocks(
        self,
        *,
        blocks: list[ParsedBlock],
        recurring: set[str],
    ) -> list[ParsedBlock]:
        kept: list[ParsedBlock] = []
        signatures: dict[str, ParsedBlock] = {}
        token_cache: list[tuple[ParsedBlock, set[str]]] = []
        decisions: list[BlockDeduplicationDecision] = []
        for block in blocks:
            decision = self._decision_for(
                block=block,
                recurring=recurring,
                signatures=signatures,
                token_cache=token_cache,
            )
            decisions.append(decision)
            if decision.dedup_status == "dropped":
                continue
            kept.append(self._annotate_block(block=block, decision=decision))
            self._record_kept_block(
                block=kept[-1], signatures=signatures, token_cache=token_cache
            )
        self._record_run_stats(total_seen=len(blocks), kept=kept, decisions=decisions)
        return kept

    def _decision_for(
        self,
        *,
        block: ParsedBlock,
        recurring: set[str],
        signatures: dict[str, ParsedBlock],
        token_cache: list[tuple[ParsedBlock, set[str]]],
    ) -> BlockDeduplicationDecision:
        signature = self._signature(block.text)
        repeated_pattern = (
            signature in recurring and self._is_repeated_pattern_candidate(block=block)
        )
        if repeated_pattern:
            return self._drop_decision(block=block, method="repeated_header_footer")
        if signature in recurring and self._is_boilerplate(block=block):
            return self._drop_decision(block=block, method="boilerplate")
        earlier = signatures.get(signature)
        if earlier is not None:
            return self._exact_duplicate_decision(block=block, earlier=earlier)
        return self._near_duplicate_decision(block=block, token_cache=token_cache)

    def _exact_duplicate_decision(
        self,
        *,
        block: ParsedBlock,
        earlier: ParsedBlock,
    ) -> BlockDeduplicationDecision:
        return self._drop_decision(
            block=block,
            method="exact_hash",
            duplicate_of=earlier.block_id,
            confidence=1.0,
        )

    def _near_duplicate_decision(
        self,
        *,
        block: ParsedBlock,
        token_cache: list[tuple[ParsedBlock, set[str]]],
    ) -> BlockDeduplicationDecision:
        candidate_tokens = self.similarity_engine.tokenize_set(block.text)
        match = self._best_near_duplicate(
            candidate_tokens=candidate_tokens,
            token_cache=token_cache,
        )
        if match is None:
            return self._keep_decision(block=block)
        earlier, similarity = match
        if self._should_bypass(block=block, confidence=similarity):
            return self._keep_decision(
                block=block,
                method="near_duplicate",
                confidence=similarity,
                bypass_reason="legal_sensitive",
            )
        return self._drop_decision(
            block=block,
            method="near_duplicate",
            duplicate_of=earlier.block_id,
            confidence=similarity,
        )

    def _best_near_duplicate(
        self,
        *,
        candidate_tokens: set[str],
        token_cache: list[tuple[ParsedBlock, set[str]]],
    ) -> tuple[ParsedBlock, float] | None:
        best_match: tuple[ParsedBlock, float] | None = None
        for earlier, existing_tokens in token_cache:
            similarity = self.similarity_engine.jaccard_similarity(
                candidate_tokens, existing_tokens
            )
            if similarity < self.config.near_duplicate_threshold:
                continue
            if best_match is None or similarity > best_match[1]:
                best_match = (earlier, similarity)
        return best_match

    def _should_bypass(self, *, block: ParsedBlock, confidence: float) -> bool:
        doc_type = (block.doc_type or "").lower()
        block_type = (block.block_type or "").lower()
        return (
            doc_type in self.config.legal_sensitive_document_types
            and block_type in self.config.legal_sensitive_block_types
            and confidence < self.config.legal_sensitive_threshold
        )

    def _record_kept_block(
        self,
        *,
        block: ParsedBlock,
        signatures: dict[str, ParsedBlock],
        token_cache: list[tuple[ParsedBlock, set[str]]],
    ) -> None:
        signature = self._signature(block.text)
        signatures[signature] = block
        token_cache.append((block, self.similarity_engine.tokenize_set(block.text)))

    def _record_run_stats(
        self,
        *,
        total_seen: int,
        kept: list[ParsedBlock],
        decisions: list[BlockDeduplicationDecision],
    ) -> None:
        skipped = total_seen - len(kept)
        self.last_stats = DeduplicationStats(
            total_seen=total_seen,
            total_skipped=skipped,
        )
        self.last_report = DeduplicationRunReport(decisions=decisions)
        logger.info(
            "Block dedup finished: total_seen=%d total_skipped=%d skip_ratio=%.4f",
            self.last_stats.total_seen,
            self.last_stats.total_skipped,
            self.last_stats.skip_ratio,
        )

    def _annotate_block(
        self,
        *,
        block: ParsedBlock,
        decision: BlockDeduplicationDecision,
    ) -> ParsedBlock:
        metadata = dict(block.metadata)
        metadata["dedup_status"] = decision.dedup_status
        metadata["dedup_method"] = decision.dedup_method
        metadata["near_duplicate_of"] = decision.near_duplicate_of
        metadata["dedup_confidence"] = decision.dedup_confidence
        metadata["dedup_bypass_reason"] = decision.dedup_bypass_reason
        return block.model_copy(update={"metadata": metadata})

    def _keep_decision(
        self,
        *,
        block: ParsedBlock,
        method: str | None = None,
        confidence: float | None = None,
        bypass_reason: str | None = None,
    ) -> BlockDeduplicationDecision:
        return BlockDeduplicationDecision(
            block_id=block.block_id,
            dedup_status="kept",
            dedup_method=method,
            near_duplicate_of=None,
            dedup_confidence=confidence,
            dedup_bypass_reason=bypass_reason,
        )

    def _drop_decision(
        self,
        *,
        block: ParsedBlock,
        method: str,
        duplicate_of: str | None = None,
        confidence: float | None = None,
    ) -> BlockDeduplicationDecision:
        return BlockDeduplicationDecision(
            block_id=block.block_id,
            dedup_status="dropped",
            dedup_method=method,
            near_duplicate_of=duplicate_of,
            dedup_confidence=confidence,
            dedup_bypass_reason=None,
        )

    def _repeated_patterns(self, blocks: list[ParsedBlock]) -> set[str]:
        pages_by_signature: dict[str, set[int]] = {}
        for block in blocks:
            if not self._is_repeated_pattern_candidate(block=block):
                continue
            signature = self._signature(block.text)
            pages_by_signature.setdefault(signature, set()).add(block.page)
        return {
            signature
            for signature, pages in pages_by_signature.items()
            if len(pages) >= self.config.repeated_pattern_min_pages
        }

    def _is_repeated_pattern_candidate(self, *, block: ParsedBlock) -> bool:
        if block.order_in_page is None:
            return False
        return block.order_in_page <= self.config.header_footer_order_cutoff

    def _is_boilerplate(self, *, block: ParsedBlock) -> bool:
        tokens = self.text_normalizer.tokenize_words(block.text)
        if not tokens:
            return True
        unique_ratio = len(set(tokens)) / len(tokens)
        return unique_ratio <= self.config.boilerplate_unique_token_ratio

    def _signature(self, text: str) -> str:
        normalized = " ".join(self.text_normalizer.tokenize_non_whitespace(text))
        return hashlib.sha256(normalized.lower().encode("utf-8")).hexdigest()
