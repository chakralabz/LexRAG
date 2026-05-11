# LexRAG Progress Report

Last updated: 2026-04-20 (Asia/Kolkata)
Phase: 1 (Week 1-2) Baseline Ingestion

## Objective Status
Documents in -> chunks out -> dense retrieval functional -> evaluation baseline recorded.

## What The Project Can Do Today
- Parse PDF and HTML legal documents with primary/fallback parser orchestration.
- Chunk documents with interchangeable strategy classes (semantic/fixed) using a stable chunker interface.
- Deduplicate near-identical chunks before indexing.
- Generate embeddings in batches and store them for dense retrieval.
- Index the same chunks into BM25 sparse storage for lexical retrieval experiments.
- Run dense retrieval over indexed chunks using query embedding + vector search.
- Execute retrieval evaluation and persist baseline/ablation metrics as JSON artifacts.

## Infrastructure Readiness
- Docker stack now includes:
  - Qdrant (dense vector DB)
  - Elasticsearch (BM25 lexical search)
  - Redis (cache/session support)
  - Langfuse (observability)
- Store adapters support real backends and in-memory test mode through the same OOP interface.

## Debuggability and Operations
- Added baseline ingestion runner:
  - `scripts/run_phase1_baseline_ingestion.py`
- Runner flow:
  - ingest directory
  - write to Qdrant + Elasticsearch
  - run smoke dense query
  - emit detailed JSON report (`progress/phase1_baseline_ingestion_report.json`)

## Quality Gates
- Lint and typing gates configured and passing in current workspace.
- Non-slow test suite passing.
- Eval gate workflow configured to block MRR regression > 3pp from baseline.

## Known Limits in Current Phase
- Phase 1 generation-level faithfulness metrics are intentionally stubbed until Phase 3.
- Sparse retriever/hybrid/reranker pipeline is planned for Phase 2.
