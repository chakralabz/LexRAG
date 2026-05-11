"""Typed dependency bundle for the serving composition root."""

from __future__ import annotations

from dataclasses import dataclass

from lexrag.context_builder import LLMContextBuilder
from lexrag.generation import AnswerGenerator
from lexrag.ingestion.jobs import IngestJobManager
from lexrag.ingestion.pipeline import IngestPipeline
from lexrag.retrieval.base import Retriever


@dataclass(frozen=True, slots=True)
class RuntimeDependencies:
    """Capture the production collaborators used by HTTP request handlers."""

    ingestion_pipeline: IngestPipeline
    ingest_job_manager: IngestJobManager
    retriever: Retriever
    context_builder: LLMContextBuilder
    generator: AnswerGenerator | None
