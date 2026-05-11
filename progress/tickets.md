# LexRAG Tickets (Phase 1)

Last updated: 2026-04-20 (Asia/Kolkata)

## Completed This Phase
- [x] `scripts/download_corpus.sh` added; corpus source rationale documented in ADR-000.
- [x] Parser stack implemented with `DoclingParser` primary and `PyMuPDFParser` fallback for PDF/HTML.
- [x] Chunking implemented with interface-driven design (`Chunker`), plus `SemanticChunker` and `FixedSizeChunker`.
- [x] Deduplication implemented (`MinHashDeduplicator`) with threshold configuration and run stats logging (`total_seen`, `total_skipped`, `skip_ratio`).
- [x] Embedding implemented with batch flow (`BGEEmbedder`, default batch size 32) and unit-normalized vectors.
- [x] Dense + sparse index managers implemented with idempotent upsert/index semantics and `chunk_id` join key.
- [x] Ingestion pipeline implemented end-to-end: parse -> chunk -> dedup -> embed -> dense upsert -> sparse index.
- [x] Dense retriever implemented: query embedding -> vector search -> chunk output with metadata filtering.
- [x] Retrieval eval metrics implemented: `MRR@K`, `NDCG@K`, `Recall@K`.
- [x] Eval harness implemented and wired to dataset/results artifacts.
- [x] Chunking ablation script implemented and results recorded.
- [x] Eval CI gate implemented with regression threshold and summary output in workflow step summary.
- [x] Production-like local infrastructure hardened with Docker services for real Qdrant + Elasticsearch + Redis + Langfuse.
- [x] Store layer upgraded to pluggable backends: in-memory for tests, real service backends for production-like ingestion.
- [x] Phase 1 baseline ingestion runner script added for repeatable operations and easier debugging/handoff.

## Verification Snapshot
- `make lint` passes (ruff + mypy).
- `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/ -m "not slow"` passes.
- Baseline eval artifact present: `eval/results/phase1_baseline.json`.
- Chunking ablation artifact present: `eval/results/chunking_ablation.json`.
- CI gate workflow present: `.github/workflows/eval_gate.yml`.
- Baseline ingestion runner available: `scripts/run_phase1_baseline_ingestion.py`.

## Metrics Snapshot (Current Artifacts)
- Phase 1 baseline (`eval/results/phase1_baseline.json`): MRR@5=`0.745667`, NDCG@5=`0.758969`, Recall@10=`1.0`.
- Chunking ablation (`eval/results/chunking_ablation.json`):
  - fixed-size: MRR@5=`0.226`, Recall@10=`0.64`
  - semantic: MRR@5=`0.6`, Recall@10=`0.94`
  - decision in artifact: `semantic`

## Phase Checkpoint Status
- [x] Ingestion pipeline is operational and integration-tested.
- [x] Baseline eval results are committed.
- [x] Ablation row/doc updates are present.
- [x] Eval gate workflow is active and enforces MRR regression threshold.

## Current System Capabilities (What It Can Do)
- Ingestion pipeline accepts PDF/HTML documents and normalizes parsed output via parser fallback chain.
- Chunking is strategy-driven (`SemanticChunker` or `FixedSizeChunker`) through a shared interface.
- Deduplication removes near-duplicate chunks before embedding/indexing and records operational ratios.
- Embedding is batched with normalization, then indexed in both dense and sparse stores.
- Dense retrieval is available end-to-end through query embedding and vector search.
- Eval harness computes retrieval metrics and writes reproducible artifacts for ablation/governance.
- Real infrastructure mode now supports Qdrant (dense) + Elasticsearch BM25 (sparse) using Docker services.

## How To Run Phase 1 Baseline Ops
- Start infra: `docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up -d`
- Run ingestion baseline: `python scripts/run_phase1_baseline_ingestion.py --input data/raw --limit 100 --backend real`
- Read report: `progress/phase1_baseline_ingestion_report.json`
- Optional convenience target: `make ingest-phase1`

## Next Backlog Slot
- [ ] Add/refresh Phase 2 retrieval tickets (sparse retriever hardening, hybrid RRF fusion, reranker, decomposition, ablations).
