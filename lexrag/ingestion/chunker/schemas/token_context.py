"""Token lineage model for fixed-window chunking."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class TokenContext(BaseModel):
    """Associates one token with its originating parsed block."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    token: str = Field(description="Single tokenizer output token.")
    block: ParsedBlock = Field(description="Parsed block that produced the token.")
