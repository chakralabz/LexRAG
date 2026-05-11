"""HTTP request contract for ingestion submission."""

from __future__ import annotations

from pathlib import PurePath

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class IngestRequest(BaseModel):
    """Capture trusted ingest-root-relative document references."""

    model_config = ConfigDict(frozen=True)

    documents: list[str] = Field(
        min_length=1,
        validation_alias=AliasChoices("documents", "paths"),
    )
    idempotency_key: str | None = Field(default=None, min_length=1)

    @field_validator("documents")
    @classmethod
    def _validate_documents(cls, documents: list[str]) -> list[str]:
        for document in documents:
            cls._validate_document(document=document)
        return documents

    @classmethod
    def _validate_document(cls, *, document: str) -> None:
        cleaned = document.strip()
        if not cleaned:
            raise ValueError("document references must not be empty")
        path = PurePath(cleaned)
        if path.is_absolute():
            raise ValueError("document references must be relative to INGEST_INPUT_DIR")
        if ".." in path.parts:
            raise ValueError("document references must not escape INGEST_INPUT_DIR")
