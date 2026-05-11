# AGENTS.md — LexRAG Build Plan

> This document defines **what gets built, in what order, and how**.
> Every phase ends with a working, evaluated system — not a half-built one.
> Every commit is described precisely. Read this before opening any editor.

---

## Core Rules for Every Agent / Contributor

1. **One commit = one logical unit.** If you need the word "and" to describe
   what a commit does, split it into two commits.

2. **No commit without a passing test.** Unit tests for the component being
   added must be written in the same commit. Not after. Not "later."

3. **No component is added speculatively.** Before adding a component,
   state the hypothesis ("hybrid retrieval will improve MRR@5 by >5%").
   After adding it, run eval and record the result. If it doesn't improve
   the metric → revert or document why you kept it anyway.

4. **The eval harness is the source of truth.** Human intuition about
   whether something "works better" is not evidence. The eval numbers are.

5. **`docs/ablation.md` is updated in the same commit as the component
   that changes a metric.** Never let it drift.

6. Never make a commit by yourself instead just give me the commit and description like format and all
   then I will execute the commit after verifying your changes

7. **One class per file.** Do not define multiple production classes in a
   single file. Each class gets its own module.

8. **No static/class methods for core logic.** Prefer instance methods and
   object state.

9. **Function length limit (funlen).** Every function/method must stay within
   40 lines and 40 statements. If it grows beyond that, split it into smaller
   helper methods.

10. **Small-method OOP style.** Methods should do one responsibility only:
    validate input, transform data, or orchestrate calls — not all three.

---

## Agent Roles

LexRAG development is structured around four agent roles.
In a solo build, you play all four. In a team, assign them explicitly.

### INGESTION_AGENT
Owns everything in `ingestion/` and `indexing/`.
Responsible for: document parsing, chunking, embedding, deduplication,
index management, ingestion pipeline orchestration.
Does NOT touch retrieval or generation logic.

### RETRIEVAL_AGENT
Owns everything in `retrieval/`.
Responsible for: dense retrieval, sparse retrieval, hybrid fusion,
reranking, query decomposition.
Reads from indexes but never writes to them.
Does NOT touch generation logic.

### GENERATION_AGENT
Owns everything in `generation/`.
Responsible for: LLM inference, constrained citation formatting,
faithfulness gating, uncertainty quantification.
Reads retrieval outputs but never calls retrieval directly.

### SERVING_AGENT
Owns everything in `serving/`, `observability/`, `infra/`, `frontend/`.
Responsible for: API, caching, middleware, CI/CD, deployment, monitoring.
Integrates components built by the other three agents.

### EVAL_AGENT
Not a build agent — a validation role.
Runs `eval/run_eval.py` after every phase.
Writes the ablation entry for the phase.
If metrics regress: blocks merge, opens issue with root cause hypothesis.

---

## Phase Overview

| Phase | Owner | Duration | Deliverable |
|---|---|---|---|
| 0 | All | Day 1 | Repo skeleton, schema, tooling |
| 1 | INGESTION_AGENT | Week 1–2 | Baseline pipeline + first eval |
| 2 | RETRIEVAL_AGENT | Week 3–4 | Hybrid retrieval + reranker |
| 3 | GENERATION_AGENT | Week 5–6 | Faithfulness gate + citation forcing |
| 4 | SERVING_AGENT | Week 7–8 | Production-hardened API + CI/CD |
| 5 | SERVING_AGENT | Week 9–10 | Frontend + deployment + launch |

---

## Phase 0 — Repository Bootstrap

**Goal:** Every subsequent agent starts from a clean, consistent foundation.
**Duration:** Day 1. Should take < 4 hours.

---

### Commit 0.1 — Repo skeleton

```
chore: initialize repo structure

- Create all top-level directories per SKILL.md §1
- Add .gitignore (Python, Node, .env, __pycache__, *.pyc, .venv)
- Add .env.example with all variables from SKILL.md §6 (no values)
- Add empty README.md placeholder
- Add empty SKILL.md placeholder (copy from template)
- Add empty AGENTS.md placeholder (copy from template)
```

Files touched: `.gitignore`, `.env.example`, `README.md`, directory structure.

---

### Commit 0.2 — Pydantic schema

```
feat(schema): add core data models

- Add indexing/schema.py: Chunk, ChunkMetadata, QAPair (per SKILL.md §2)
- Add tests/unit/test_schema.py: validate Chunk construction,
  chunk_id format, QAPair difficulty enum
```

Files touched: `indexing/schema.py`, `tests/unit/test_schema.py`.

Acceptance: `pytest tests/unit/test_schema.py` passes.

---

### Commit 0.3 — Tooling

```
chore: configure pyproject.toml, ruff, mypy

- Add pyproject.toml with all dependencies from SKILL.md §7
- Configure ruff (line-length=88, select E/F/I)
- Configure mypy (strict=false, ignore_missing_imports=true)
- Add Makefile with targets: lint, test, eval, ingest, serve
```

Files touched: `pyproject.toml`, `Makefile`.

Acceptance: `make lint` runs clean on current codebase.

---

### Commit 0.4 — Docker Compose (dev stack)

```
chore: add docker-compose for local dev stack

- Add infra/docker-compose.yml with services:
  - qdrant (qdrant/qdrant:latest, port 6333)
  - elasticsearch (8.x, port 9200, single-node, no security for dev)
  - redis (latest, port 6379)
  - langfuse (optional, port 3001)
- Add infra/docker-compose.dev.yml with volume mounts for hot reload
- Document: `docker compose up -d` in README Quick Start
```

Files touched: `infra/docker-compose.yml`, `infra/docker-compose.dev.yml`.

Acceptance: `docker compose up -d` starts all services without errors.
`curl http://localhost:6333/health` returns 200.

---

### Commit 0.5 — Eval harness skeleton

```
feat(eval): add eval harness skeleton and sample QA pairs

- Add eval/metrics.py: stub implementations of all metric functions
  (return 0.0, raise NotImplementedError body) with docstrings
- Add eval/run_eval.py: CLI skeleton (argparse, loads QA pairs, prints
  "Not implemented" — to be filled in Phase 1)
- Add eval/dataset/schema.md: document QAPair JSON format
- Add eval/dataset/qa_pairs.json: 10 seed QA pairs (hand-written,
  across factoid/multi_hop/unanswerable) for smoke testing
- Add tests/unit/test_metrics.py: test metric functions with known inputs
```

Files touched: `eval/metrics.py`, `eval/run_eval.py`,
`eval/dataset/schema.md`, `eval/dataset/qa_pairs.json`,
`tests/unit/test_metrics.py`.

Acceptance: `python eval/run_eval.py --split ci` runs without import errors.

---

### Commit 0.6 — GitHub Actions: lint CI

```
ci: add lint workflow

- Add .github/workflows/lint.yml
  - Triggers: push to any branch, PR to main
  - Steps: checkout, setup Python 3.11, install deps, ruff, mypy
- Add .github/workflows/eval_gate.yml (skeleton only — no eval yet)
  - Contains TODO comment: "Eval gate activated in Phase 1, Commit 1.7"
```

Files touched: `.github/workflows/lint.yml`,
`.github/workflows/eval_gate.yml`.

---

**Phase 0 checkpoint:**
- [ ] `docker compose up -d` → all services healthy
- [ ] `make lint` → clean
- [ ] `pytest tests/` → all pass (6 tests)
- [ ] `python eval/run_eval.py --split ci` → runs without errors
- [ ] `.env.example` has every variable needed for the full system
- [ ] First entry in `docs/decisions.md` explaining schema design choices

---

## Phase 1 — Baseline Ingestion Pipeline

**Goal:** Documents go in, chunks come out, basic retrieval works,
first eval numbers are recorded.
**Owner:** INGESTION_AGENT
**Duration:** Week 1–2

---

### Commit 1.1 — Corpus download script

```
feat(scripts): add corpus download script

- Add scripts/download_corpus.sh
  - Downloads 50 EDGAR 10-K filings (via SEC EDGAR full-text search API)
  - Downloads EU AI Act (EUR-Lex PDF)
  - Downloads 20 public domain court opinions (CourtListener API)
  - Saves to data/raw/ (gitignored)
  - Logs: total files, total MB, any failures
- Add data/.gitignore (ignore raw/, keep .gitkeep)
- Document corpus sources in docs/decisions.md (ADR-000)
```

Files touched: `scripts/download_corpus.sh`, `data/.gitignore`,
`docs/decisions.md`.

Note: Do not commit actual corpus files. Only the download script.

---

### Commit 1.2 — PDF parser

```
feat(ingestion): add document parser

- Add ingestion/parser.py
  - DoclingParser: uses docling to extract {page, section, text} dicts
  - PyMuPDFParser: fallback parser using pymupdf
  - parse_document(path) → list[dict]: tries docling, falls back to pymupdf,
    logs which parser was used
  - Handles: PDFs, HTML files (for court opinions)
- Add tests/unit/test_parser.py
  - Test with fixture PDF (3-page test doc committed to tests/fixtures/)
  - Assert page count, section extraction, text non-empty
  - Test fallback behavior
```

Files touched: `ingestion/parser.py`, `tests/unit/test_parser.py`,
`tests/fixtures/sample.pdf`.

Acceptance: `pytest tests/unit/test_parser.py` passes.

---

### Commit 1.3 — Semantic chunker + fixed-size chunker

```
feat(ingestion): add semantic and fixed-size chunkers

- Add ingestion/chunker.py
  - SemanticChunker: cosine similarity boundary detection
    (all-MiniLM-L6-v2, threshold=0.75, min=128, max=512 tokens)
  - FixedSizeChunker: 512 tokens, 50-token overlap (baseline)
  - Both implement: chunk(pages: list[dict]) -> list[Chunk]
  - Boundary artifact warning: log if chunk starts with lowercase
- Add tests/unit/test_chunker.py
  - Test SemanticChunker: verify no chunks exceed MAX_CHUNK_TOKENS
  - Test SemanticChunker: verify chunks are Chunk instances
  - Test FixedSizeChunker: verify overlap behavior
  - Test: boundary artifact detection fires on known bad input
```

Files touched: `ingestion/chunker.py`, `tests/unit/test_chunker.py`.

Acceptance: `pytest tests/unit/test_chunker.py` passes.

---

### Commit 1.4 — Deduplicator

```
feat(ingestion): add MinHash LSH deduplicator

- Add ingestion/deduplicator.py
  - MinHashDeduplicator: datasketch LSH, threshold=0.85
  - deduplicate(chunks: list[Chunk]) -> list[Chunk]: returns unique chunks
  - Logs: total_seen, total_skipped, skip_ratio
- Add tests/unit/test_deduplicator.py
  - Test: identical chunks → one survives
  - Test: near-duplicate (85%+ similar) → one survives
  - Test: clearly different chunks → both survive
```

Files touched: `ingestion/deduplicator.py`,
`tests/unit/test_deduplicator.py`.

---

### Commit 1.5 — BGE-M3 embedder

```
feat(ingestion): add BGE-M3 batch embedder

- Add ingestion/embedder.py
  - BGEEmbedder: BAAI/bge-m3 via sentence-transformers
  - embed_chunks(chunks: list[Chunk]) -> list[Chunk]: adds embedding field
  - Batches by EMBED_BATCH_SIZE env var (default 32)
  - Normalizes all embeddings before returning
  - Logs: total chunks, batches, wall time, chunks/sec
- Add tests/unit/test_embedder.py
  - Test: output vectors are unit norm (within 1e-6)
  - Test: batch embed produces same result as single embed
  - Test: embedding dim matches BGE-M3 spec (1024)
```

Files touched: `ingestion/embedder.py`, `tests/unit/test_embedder.py`.

Note: These tests will be slow (model load). Mark with `@pytest.mark.slow`.
Fast CI skips slow tests: `pytest -m "not slow"`.

---

### Commit 1.6 — Qdrant + Elasticsearch index managers

```
feat(indexing): add Qdrant and BM25 index managers

- Add indexing/qdrant_store.py
  - QdrantStore: upsert_chunks, search_dense, delete_collection
  - Upsert is idempotent (chunk_id as point ID)
  - Payload fields indexed per SKILL.md §3.2
- Add indexing/bm25_store.py
  - BM25Store: index_chunks, search_bm25
  - chunk_id kept in sync with Qdrant
- Add tests/integration/test_stores.py
  - Requires running Qdrant + ES (mark: @pytest.mark.integration)
  - Test: upsert 5 chunks → search returns them
  - Test: re-upsert same chunks → no duplicates
  - Test: metadata filter works (doc_type=sec_filing)
  - Test: BM25 search returns chunk_ids matching Qdrant
```

Files touched: `indexing/qdrant_store.py`, `indexing/bm25_store.py`,
`tests/integration/test_stores.py`.

Acceptance: `pytest tests/integration/ -m integration` passes against
local docker stack.

---

### Commit 1.7 — Ingestion pipeline + basic dense retriever

```
feat(ingestion): add end-to-end ingestion pipeline

feat(retrieval): add basic dense retriever

- Add ingestion/pipeline.py
  - IngestPipeline: orchestrates parse → chunk → deduplicate → embed →
    upsert (Qdrant) → index (BM25)
  - CLI: python ingestion/pipeline.py --input <dir> --limit <N>
  - Progress logging: per-document, plus summary at end
- Add retrieval/dense_retriever.py
  - DenseRetriever: embed query → Qdrant search → return list[Chunk]
  - Supports metadata filters (pass-through to Qdrant payload filter)
- Add tests/integration/test_pipeline.py
  - Ingest 3 test documents → verify chunks appear in Qdrant and ES
  - Query dense retriever → verify non-empty results
```

Files touched: `ingestion/pipeline.py`, `retrieval/dense_retriever.py`,
`tests/integration/test_pipeline.py`.

---

### Commit 1.8 — Implement eval metrics + run Phase 1 eval

```
feat(eval): implement retrieval metrics and run Phase 1 baseline

- Implement eval/metrics.py: mrr_at_k, ndcg_at_k, recall_at_k
  (faithfulness and bertscore stubbed — need generation layer)
- Implement eval/run_eval.py: full retrieval eval against qa_pairs.json
  (uses DenseRetriever + FixedSizeChunker for this baseline)
- Add eval/dataset/qa_pairs.json: expand to 50 QA pairs
  (stratified: 20 factoid, 15 multi_hop, 10 unanswerable, 5 temporal)
- Run eval. Record results to eval/results/phase1_baseline.json
- Update docs/ablation.md: Phase 1 baseline row
  (Dense only, FixedSize chunking)

docs/ablation.md entry:
| Phase 1a | Dense only | Fixed-size | — | MRR@5: TBD | Recall@10: TBD |
```

Files touched: `eval/metrics.py`, `eval/run_eval.py`,
`eval/dataset/qa_pairs.json`, `eval/results/phase1_baseline.json`,
`docs/ablation.md`.

**This is the first real eval checkpoint. Do not proceed to Phase 2 without
these numbers.**

---

### Commit 1.9 — Chunking ablation

```
experiment(eval): semantic chunking vs fixed-size ablation

- Add scripts/benchmark_chunking.py
  - Runs ingestion twice: once with FixedSizeChunker, once with
    SemanticChunker
  - Runs retrieval eval on same 50 QA pairs for both
  - Outputs comparison table to stdout + saves to
    eval/results/chunking_ablation.json
- Run the script. Record results.
- Update docs/ablation.md: add chunking comparison row
- Update docs/decisions.md: ADR-001 with empirical evidence
- Switch ingestion pipeline default to SemanticChunker if MRR improves
```

Files touched: `scripts/benchmark_chunking.py`,
`eval/results/chunking_ablation.json`, `docs/ablation.md`,
`docs/decisions.md`, `ingestion/pipeline.py` (default chunker switch).

---

### Commit 1.10 — Activate eval CI gate

```
ci: activate eval gate in GitHub Actions

- Update .github/workflows/eval_gate.yml
  - Run `python eval/run_eval.py --split ci` on every PR to main
  - Fail if MRR@5 < (baseline − 0.03)
  - Fail if faithfulness < (baseline − 0.02) [once gen layer exists]
  - Save baseline from eval/results/phase1_baseline.json
  - Post metric summary as PR comment
```

Files touched: `.github/workflows/eval_gate.yml`.

---

**Phase 1 checkpoint:**
- [ ] Ingest 100 documents without errors
- [ ] Dense retrieval returns non-empty results for all 50 eval questions
- [ ] `eval/results/phase1_baseline.json` committed with real numbers
- [ ] `docs/ablation.md` has Phase 1a and Phase 1b rows
- [ ] `docs/decisions.md` has ADR-000 (corpus) and ADR-001 (chunking)
- [ ] CI lint + eval gate both green
- [ ] `pytest tests/ -m "not slow"` → all pass

---

## Phase 2 — Hybrid Retrieval + Reranking

**Goal:** Improve retrieval metrics via BM25 fusion and cross-encoder reranking.
**Owner:** RETRIEVAL_AGENT
**Duration:** Week 3–4

---

### Commit 2.1 — BM25 sparse retriever

```
feat(retrieval): add BM25 sparse retriever

- Add retrieval/sparse_retriever.py
  - SparseRetriever: query → Elasticsearch BM25 search → list[Chunk]
  - Supports same metadata filters as DenseRetriever
- Add tests/unit/test_sparse_retriever.py
  - Test: known exact-match term in corpus → appears in top 3
  - Test: metadata filter respected
```

Files touched: `retrieval/sparse_retriever.py`,
`tests/unit/test_sparse_retriever.py`.

---

### Commit 2.2 — RRF hybrid fusion

```
feat(retrieval): add hybrid retriever with RRF fusion

- Add retrieval/hybrid_retriever.py
  - HybridRetriever: runs DenseRetriever + SparseRetriever in parallel
    (asyncio.gather), applies RRF fusion (k=60), returns merged list[Chunk]
  - RETRIEVAL_ALPHA env var controls dense weight in pre-fusion scoring
  - Logs: dense_results_count, sparse_results_count, fusion_time_ms
- Add tests/unit/test_hybrid_retriever.py
  - Test: chunks appearing in both lists rank higher than single-list chunks
  - Test: RRF formula correctness (manual calculation vs implementation)
  - Test: alpha=1.0 → pure dense, alpha=0.0 → pure sparse
```

Files touched: `retrieval/hybrid_retriever.py`,
`tests/unit/test_hybrid_retriever.py`.

---

### Commit 2.3 — Hybrid retrieval ablation

```
experiment(eval): dense vs hybrid retrieval ablation

- Run eval with HybridRetriever. Compare against Phase 1 dense baseline.
- Record to eval/results/phase2_hybrid.json
- Update docs/ablation.md: hybrid row
- Update docs/decisions.md: ADR-002 (hybrid retrieval — evidence for keeping it)
- Update ingestion pipeline to use HybridRetriever as default
  IF MRR@5 improves by >3pp. Document decision either way.
```

Files touched: `eval/results/phase2_hybrid.json`, `docs/ablation.md`,
`docs/decisions.md`.

Hypothesis: MRR@5 improves ≥5pp over dense-only.

---

### Commit 2.4 — Cross-encoder reranker

```
feat(retrieval): add cross-encoder reranker

- Add retrieval/reranker.py
  - CrossEncoderReranker: ms-marco-MiniLM-L-12-v2
  - rerank(query, chunks: list[Chunk], top_k=5) -> list[Chunk]
  - Takes top N=20 from hybrid retriever, returns top K=5 after reranking
  - Logs: score distribution (min, max, mean, p25, p75)
- Add tests/unit/test_reranker.py
  - Test: reranker changes ordering relative to retriever
  - Test: top_k respected
  - Test: output is subset of input (no hallucinated chunks)
```

Files touched: `retrieval/reranker.py`, `tests/unit/test_reranker.py`.

---

### Commit 2.5 — Reranker ablation

```
experiment(eval): hybrid vs hybrid+reranker ablation

- Run eval: HybridRetriever + CrossEncoderReranker vs HybridRetriever only
- Record to eval/results/phase2_reranker.json
- Update docs/ablation.md
- Update docs/decisions.md: ADR-003 (reranker)
```

Files touched: `eval/results/phase2_reranker.json`, `docs/ablation.md`,
`docs/decisions.md`.

Hypothesis: MRR@5 improves ≥5pp. Latency increases ~150ms.

---

### Commit 2.6 — Query decomposer

```
feat(retrieval): add multi-hop query decomposer

- Add retrieval/query_decomposer.py
  - QueryDecomposer: heuristic multi-hop classifier + LLM decomposition
  - is_multihop(question: str) -> bool: keyword heuristic
  - decompose(question: str) -> list[str]: LLM call → ≤3 sub-queries
  - Full retrieval path: decompose → retrieve each → merge → rerank
  - Only activates if is_multihop() returns True
  - Logs: classified_as_multihop, sub_queries, merge_strategy
- Add tests/unit/test_query_decomposer.py
  - Test: factoid question → is_multihop=False (no decomposition)
  - Test: multi-hop question → is_multihop=True, ≤3 sub-queries returned
  - Test: decomposed results merged correctly before reranking
```

Files touched: `retrieval/query_decomposer.py`,
`tests/unit/test_query_decomposer.py`.

---

### Commit 2.7 — Multi-hop ablation + Phase 2 full eval

```
experiment(eval): multi-hop ablation + Phase 2 summary eval

- Run eval on multi_hop difficulty subset only:
  with/without query decomposition
- Run full Phase 2 eval (all 50 QA pairs): full retrieval stack
- Record to eval/results/phase2_multihop_ablation.json
  and eval/results/phase2_full.json
- Update docs/ablation.md: complete Phase 2 rows
- Update docs/failures.md: document any failure cases discovered
- Update CI baseline to phase2_full.json
```

Files touched: `eval/results/`, `docs/ablation.md`, `docs/failures.md`,
`.github/workflows/eval_gate.yml` (update baseline path).

---

**Phase 2 checkpoint:**
- [ ] `eval/results/phase2_full.json` shows MRR@5 > 0.70
- [ ] Ablation table has 5 rows (dense, hybrid, +reranker, +decompose, full P2)
- [ ] Multi-hop subset shows clear improvement with decomposition
- [ ] `docs/failures.md` has at least 2 failure cases documented
- [ ] All unit tests pass
- [ ] CI green

---

## Phase 3 — Generation + Faithfulness

**Goal:** Add LLM generation with citation forcing and faithfulness gating.
**Owner:** GENERATION_AGENT
**Duration:** Week 5–6

---

### Commit 3.1 — LLM inference wrapper

```
feat(generation): add vLLM/llama.cpp inference wrapper

- Add generation/generator.py
  - LLMGenerator: Qwen2.5-7B-Instruct
    - GPU path: vLLM with AWQ 4-bit
    - CPU path: llama-cpp-python with Q4_K_M
    - Auto-detects which to use via CUDA availability
  - generate(prompt: str, stream=True) -> AsyncIterator[str]
  - Context budget enforcement: trim lowest-score chunks if >3000 tokens
  - Logs: prompt_tokens, completion_tokens, time_to_first_token_ms
- Add tests/unit/test_generator.py (uses tiny model for speed)
  - Test: generates non-empty output
  - Test: streaming produces tokens incrementally
  - Test: context budget trim logic (unit test, no actual LLM)
```

Files touched: `generation/generator.py`, `tests/unit/test_generator.py`.

---

### Commit 3.2 — Citation formatter (constrained decoding)

```
feat(generation): add citation-forced generation with Outlines

- Add generation/citation_formatter.py
  - CitationFormatter: wraps LLMGenerator with Outlines grammar
  - Grammar enforces: <answer>[CLAIM] text [SOURCE: chunk_id, p.N]...</answer>
  - format_answer(question, chunks) -> CitationFormattedAnswer
  - CitationFormattedAnswer: answer_text, claims (list), citations (list)
  - Parses output into structured form after generation
- Add tests/unit/test_citation_formatter.py
  - Test: output always contains at least one [SOURCE: ...] tag
  - Test: parser correctly extracts claims and citations
  - Test: chunk_id in citations is always from the provided chunks list
```

Files touched: `generation/citation_formatter.py`,
`tests/unit/test_citation_formatter.py`.

---

### Commit 3.3 — NLI faithfulness gate

```
feat(generation): add DeBERTa-v3 NLI faithfulness gate

- Add generation/faithfulness_gate.py
  - FaithfulnessGate: cross-encoder/nli-deberta-v3-base
  - check(claims: list[str], cited_chunks: list[Chunk]) -> GateResult
  - GateResult: passed, abstained, per_claim_scores, reason
  - Gate logic per SKILL.md §3.4
  - Abstention response format per SKILL.md §3.4
- Add tests/unit/test_faithfulness_gate.py
  - Test: claim entailed by chunk → passes
  - Test: claim contradicted by chunk → abstains
  - Test: >30% neutral → low-confidence flag
  - Mark slow (model load)
```

Files touched: `generation/faithfulness_gate.py`,
`tests/unit/test_faithfulness_gate.py`.

---

### Commit 3.4 — Uncertainty quantification

```
feat(generation): add token entropy uncertainty signal

- Add generation/uncertainty.py
  - UncertaintyScorer: computes mean token log-prob from vLLM logprobs
  - score(logprobs: list[float]) -> UncertaintyResult
  - UncertaintyResult: mean_logprob, confidence_bucket (high/medium/low)
  - Thresholds: high > -0.3, medium -0.3 to -0.8, low < -0.8
- Add tests/unit/test_uncertainty.py
  - Test: known logprob sequence → correct bucket
  - Test: empty logprobs → handled gracefully
```

Files touched: `generation/uncertainty.py`,
`tests/unit/test_uncertainty.py`.

---

### Commit 3.5 — Full generation pipeline integration test

```
test(integration): end-to-end retrieval → generation test

- Add tests/integration/test_rag_pipeline.py
  - Test: query → hybrid retrieval → rerank → generate → faithfulness check
  - Assert: non-abstained answer has ≥1 citation
  - Assert: abstained answer has reason field
  - Assert: confidence_bucket is always set
  - Use 5 known-good questions from eval set
  - Mark: @pytest.mark.integration @pytest.mark.slow
```

Files touched: `tests/integration/test_rag_pipeline.py`.

---

### Commit 3.6 — Implement faithfulness metric + full Phase 3 eval

```
feat(eval): implement faithfulness + bertscore metrics, run Phase 3 eval

- Implement eval/metrics.py: faithfulness_score, bertscore_f1,
  citation_accuracy (stubs → real implementations)
- Expand eval/dataset/qa_pairs.json to 100 QA pairs
- Run full eval: retrieval + generation + faithfulness
- Record to eval/results/phase3_full.json
- Update docs/ablation.md: complete Phase 3 rows including faithfulness
- Update docs/failures.md: generation failure cases
- Add docs/decisions.md: ADR-004 (faithfulness gate design)
```

Files touched: `eval/metrics.py`, `eval/dataset/qa_pairs.json`,
`eval/results/phase3_full.json`, `docs/ablation.md`, `docs/failures.md`,
`docs/decisions.md`.

---

### Commit 3.7 — Faithfulness gate ablation

```
experiment(eval): with/without faithfulness gate ablation

- Run eval: full stack with gate vs without gate
- Measure: faithfulness score, abstention rate, answer correctness
- Record: eval/results/phase3_gate_ablation.json
- Update docs/ablation.md
- Decision: keep gate if faithfulness improves ≥10pp (it will)
```

Files touched: `eval/results/phase3_gate_ablation.json`,
`docs/ablation.md`.

---

**Phase 3 checkpoint:**
- [ ] Full pipeline works end-to-end (retrieval + generation)
- [ ] `eval/results/phase3_full.json` shows faithfulness > 0.85
- [ ] Abstention rate measured and documented
- [ ] All citation outputs have valid chunk_id references
- [ ] `docs/failures.md` has ≥4 failure cases total
- [ ] CI gate updated to include faithfulness threshold

---

## Phase 4 — Production Hardening

**Goal:** Rate limiting, caching, observability, load testing.
**Owner:** SERVING_AGENT
**Duration:** Week 7–8

### Commits 4.1–4.8 (abbreviated — same atomic structure applies)

```
4.1  feat(serving): add FastAPI app with lifespan model loading
4.2  feat(serving): add /query endpoint (non-streaming + streaming)
4.3  feat(serving): add /ingest endpoint + /health endpoint
4.4  feat(serving): add JWT auth middleware + rate limiting
4.5  feat(serving): add Redis semantic cache
4.6  feat(observability): add LangFuse trace logging wrapper
4.7  feat(observability): add Prometheus metrics + /metrics endpoint
4.8  feat(observability): add Grafana dashboard (import JSON)
4.9  test(load): add k6 load test (50 concurrent users, 60s)
4.10 docs: add Phase 4 eval snapshot + update ablation with latency numbers
```

Each commit: one component, tests in same commit, no exceptions.

**Phase 4 checkpoint:**
- [ ] `curl http://localhost:8000/health` → 200
- [ ] `curl http://localhost:8000/metrics` → Prometheus text
- [ ] Load test: P95 < 2.5s at 50 concurrent users
- [ ] LangFuse shows traces with full breakdown
- [ ] Cache hit rate > 20% on repeated queries
- [ ] `docker compose up` brings up entire stack

---

## Phase 5 — Frontend + Deployment + Launch

**Goal:** Live demo, public repo, launch post.
**Owner:** SERVING_AGENT
**Duration:** Week 9–10

### Commits 5.1–5.8 (abbreviated)

```
5.1  feat(frontend): scaffold Next.js app with streaming query UI
5.2  feat(frontend): add document upload + ingestion status UI
5.3  feat(frontend): add citation panel (click citation → highlight source)
5.4  feat(frontend): add query history + thumbs up/down feedback
5.5  feat(frontend): add ablation results dashboard page
5.6  infra: deploy backend to Fly.io + LLM inference to Modal Labs
5.7  infra: deploy frontend to Vercel + configure env vars
5.8  docs: finalize README (architecture diagram, ablation table,
     failure log link, live demo link, cost breakdown)
```

**Phase 5 checkpoint:**
- [ ] Live URL works and returns answers
- [ ] README has: diagram, ablation table, 5 failure cases, design decisions
- [ ] `eval/results/final.json` committed with all metrics
- [ ] LinkedIn Post 5 (launch post) published
- [ ] Total monthly infra cost documented (target: < $5)

---

## Commit Message Convention

```
<type>(<scope>): <short description>

Types:  feat | fix | test | experiment | docs | ci | chore | refactor
Scope:  ingestion | indexing | retrieval | generation | serving |
        eval | observability | frontend | infra | scripts | docs

Examples:
  feat(retrieval): add RRF hybrid fusion
  experiment(eval): semantic vs fixed-size chunking ablation
  fix(generation): handle empty retrieved chunks gracefully
  docs(ablation): update Phase 2 reranker results
```

**Rule:** `experiment` type commits always include results in the commit body.
Not in a separate docs commit. In the same commit. The result is the reason
the code change happened.

---

## What Done Means

A phase is done when:
1. All commits in the phase are merged to `main`
2. Eval snapshot exists in `eval/results/`
3. `docs/ablation.md` has the phase's rows with real numbers
4. CI is green
5. No TODO comments remain in the phase's code (use GitHub Issues instead)

A commit is done when:
1. `make lint` passes
2. `pytest tests/ -m "not slow"` passes
3. The commit message accurately describes what changed
4. No commented-out code
5. No print() statements (use logging)
