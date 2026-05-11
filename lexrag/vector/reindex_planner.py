"""Deterministic document-level re-index planning."""

from __future__ import annotations

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.vector.schemas import ReindexPlan


class ReindexPlanner:
    """Builds explicit re-index plans before any vector writes happen.

    Making the replacement plan explicit keeps version-aware upserts readable,
    testable, and auditable. It also gives us a stable place to evolve future
    archive or soft-delete behavior without rewriting the store facade.
    """

    def plan(self, *, incoming: list[Chunk], existing: list[Chunk]) -> ReindexPlan:
        """Return the re-index plan for one document batch.

        Args:
            incoming: Incoming chunks for one document lineage.
            existing: Existing indexed chunks for the same `doc_id`.

        Returns:
            Document-level replacement plan.
        """

        document_id = self._document_id(chunks=incoming)
        incoming_version = self._incoming_version(chunks=incoming)
        stale_chunk_ids = self._stale_chunk_ids(
            existing=existing,
            incoming_version=incoming_version,
        )
        return ReindexPlan(
            document_id=document_id,
            incoming_version=incoming_version,
            incoming_chunk_ids=[chunk.chunk_id for chunk in incoming],
            stale_chunk_ids=stale_chunk_ids,
            replacement_required=bool(stale_chunk_ids),
        )

    def _document_id(self, *, chunks: list[Chunk]) -> str:
        return chunks[0].metadata.doc_id or "unknown_doc"

    def _incoming_version(self, *, chunks: list[Chunk]) -> str | None:
        return chunks[0].metadata.document_version

    def _stale_chunk_ids(
        self,
        *,
        existing: list[Chunk],
        incoming_version: str | None,
    ) -> list[str]:
        if incoming_version is None:
            return []
        return [
            chunk.chunk_id
            for chunk in existing
            if chunk.metadata.document_version != incoming_version
        ]
