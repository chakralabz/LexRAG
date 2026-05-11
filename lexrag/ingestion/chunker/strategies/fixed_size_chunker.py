"""Deterministic fixed-window chunker used for baselines and controlled tests."""

from __future__ import annotations

from lexrag.ingestion.chunker.config.chunk_type import ChunkType
from lexrag.ingestion.chunker.config.chunking_config import ChunkingConfig
from lexrag.ingestion.chunker.config.chunking_strategy import ChunkingStrategy
from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.schemas.raw_chunk_payload import RawChunkPayload
from lexrag.ingestion.chunker.schemas.token_context import TokenContext
from lexrag.ingestion.chunker.strategies.base_chunker import BaseChunker
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class FixedSizeChunker(BaseChunker):
    """Slice parsed content into overlapping token windows with full lineage."""

    def __init__(
        self,
        *,
        chunk_size: int | None = None,
        overlap: int | None = None,
        config: ChunkingConfig | None = None,
    ) -> None:
        super().__init__(config=self._resolved_config(chunk_size=chunk_size, overlap=overlap, config=config))

    def _chunk_prepared_blocks(self, blocks: list[ParsedBlock]) -> list[Chunk]:
        """Build fixed-window chunks from already curated parsed blocks."""
        token_stream = self._token_stream(blocks=blocks)
        if not token_stream:
            return []
        raw_chunks = self._raw_chunks(token_stream=token_stream)
        built = self.chunk_model_factory.build_chunks(raw_chunks, parsed_blocks=blocks)
        return self.chunk_post_processor.process(built)

    def _token_stream(self, *, blocks: list[ParsedBlock]) -> list[TokenContext]:
        """Flatten blocks into tokens while preserving source lineage."""
        stream: list[TokenContext] = []
        for block in blocks:
            for token in self.tokenization_engine.tokenize(block.text.strip()):
                stream.append(TokenContext(token=token, block=block))
        return stream

    def _raw_chunks(self, *, token_stream: list[TokenContext]) -> list[RawChunkPayload]:
        """Create raw overlapping windows from the token stream."""
        windows = self.tokenization_engine.window_tokens(
            tokens=[context.token for context in token_stream],
            window_size=self.config.max_chunk_tokens,
            overlap=self.config.overlap_tokens,
        )
        return self._build_windows(token_stream=token_stream, windows=windows)

    def _build_windows(
        self,
        *,
        token_stream: list[TokenContext],
        windows: list[list[str]],
    ) -> list[RawChunkPayload]:
        """Build raw payloads for each fixed token window."""
        raw_chunks: list[RawChunkPayload] = []
        cursor = 0
        stride = max(self.config.max_chunk_tokens - self.config.overlap_tokens, 1)
        for window in windows:
            source_blocks = self._source_blocks(token_stream=token_stream, size=len(window), start=cursor)
            raw_chunks.append(
                RawChunkPayload(
                    text=self.tokenization_engine.detokenize(window).strip(),
                    source_blocks=source_blocks,
                    chunking_strategy=ChunkingStrategy.FIXED_TOKEN_WINDOW,
                    chunk_type=self._chunk_type(source_blocks=source_blocks),
                    token_count=len(window),
                )
            )
            cursor += stride
        return raw_chunks

    def _source_blocks(
        self,
        *,
        token_stream: list[TokenContext],
        size: int,
        start: int,
    ) -> list[ParsedBlock]:
        """Collect unique source blocks covered by one token window."""
        blocks_by_id: dict[str, ParsedBlock] = {}
        for context in token_stream[start : start + size]:
            blocks_by_id[context.block.block_id] = context.block
        return list(blocks_by_id.values())

    def _chunk_type(self, *, source_blocks: list[ParsedBlock]) -> ChunkType:
        """Resolve dominant chunk type for fixed-window output."""
        types = {block.block_type for block in source_blocks if block.block_type}
        if "table" in types:
            return ChunkType.TABLE
        if "code" in types or "code_block" in types:
            return ChunkType.CODE
        return ChunkType.PARAGRAPH

    def _resolved_config(
        self,
        *,
        chunk_size: int | None,
        overlap: int | None,
        config: ChunkingConfig | None,
    ) -> ChunkingConfig:
        """Resolve config while preserving old constructor ergonomics."""
        if config is not None:
            return config
        resolved_chunk_size = chunk_size or 512
        resolved_overlap = overlap if overlap is not None else 64
        return ChunkingConfig(
            min_chunk_tokens=min(resolved_chunk_size, 64),
            target_chunk_tokens=resolved_chunk_size,
            max_chunk_tokens=resolved_chunk_size,
            overlap_tokens=resolved_overlap,
        )
