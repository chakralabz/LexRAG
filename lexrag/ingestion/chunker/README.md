# Chunker Package

`lexrag.ingestion.chunker` is the package boundary between normalized parser
blocks and indexing-ready chunks.

## Contract

Input:
- `list[ParsedBlock]` that has already passed parsing and normalization

Output:
- `list[Chunk]` with stable IDs, lineage metadata, overlap wiring, and
  post-processing quality annotations

## Internal Pipeline

The production flow is intentionally staged:

1. `NormalizedBlockPipeline`
   Deduplicates blocks and removes low-quality parser/OCR noise.
2. `Chunker` strategy
   Materializes raw chunk candidates. The default production strategy is
   `SemanticChunker`. `FixedSizeChunker` remains available for baselines and
   controlled evals.
3. `ChunkModelFactory`
   Converts raw payloads into canonical `Chunk` models with deterministic IDs.
4. `ChunkPostProcessor`
   Adds adjacency links, audit metadata, quality flags, and retrieval-safe
   extension metadata.

`ChunkingPipeline` is the package composition root for these stages.

## Main Components

- `ChunkingPipeline`
  Orchestrates block curation and chunk materialization. Use
  `chunk_with_report()` when you want stage-level artifacts.
- `SemanticChunker`
  Planner/builder-based semantic chunking aligned to the architecture document.
- `FixedSizeChunker`
  Deterministic overlapping token windows for baselines and ablation runs.
- `ChunkingConfig`
  Shared sizing and quality thresholds for semantic chunking stages.

## Usage

```python
from lexrag.ingestion.chunker import ChunkingPipeline, ChunkingConfig, SemanticChunker

pipeline = ChunkingPipeline(
    chunker=SemanticChunker(
        config=ChunkingConfig(
            min_chunk_tokens=128,
            target_chunk_tokens=512,
            max_chunk_tokens=512,
            overlap_tokens=64,
            similarity_threshold=0.75,
        )
    )
)

result = pipeline.chunk_with_report(normalized_blocks)
chunks = result.chunks
```

## Extension Guidance

- Keep strategy-specific heuristics inside the concrete chunker, not in
  `ChunkingPipeline`.
- Preserve `Chunk`, `ChunkMetadata`, and `ParsedBlock` as the only public stage
  contracts.
- Add new strategies by implementing `Chunker`; prefer inheriting from
  `BaseChunker` if you want built-in block curation support.
