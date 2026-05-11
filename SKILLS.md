# SKILL.md — LexRAG Engineering Playbook

> This document defines **how** LexRAG is built: component conventions,
> implementation patterns, tooling decisions, and the rules every contributor
> (or AI agent) must follow before touching any file in this repo.
> Read this before writing a single line of code.

---

## 0. Repository Philosophy

LexRAG is built on three hard constraints:

1. **No component is added without a metric that justifies it.**
   Every architectural addition must be preceded by a baseline measurement
   and followed by a post-addition measurement. Ablation results live in
   `docs/ablation.md` and are updated with every phase.

2. **Every commit is atomic and reviewable.**
   A commit either adds one component, improves one component, or fixes one
   thing. "Add retrieval + reranker + cache + frontend" is not a commit — it
   is four commits. See `AGENTS.md` for the exact commit plan.

3. **Failures are first-class citizens.**
   Every significant failure mode discovered during development is logged in
   `docs/failures.md` with: query that triggered it, root cause, and fix
   applied. This document is part of the final deliverable.

---

## 1. Project Structure

```
lexrag/
├── SKILL.md                  ← You are here
├── AGENTS.md                 ← Commit plan + agent roles
├── README.md                 ← Public-facing project narrative
│
├── ingestion/                ← Phase 1: Document parsing + chunking
│   ├── parser.py             ← PDF/HTML → raw text + metadata
│   ├── chunker.py            ← Semantic chunking logic
│   ├── deduplicator.py       ← MinHash LSH dedup
│   ├── embedder.py           ← BGE-M3 embedding wrapper
│   └── pipeline.py           ← Orchestrates full ingestion flow
│
├── indexing/                 ← Phase 1: Index management
│   ├── qdrant_store.py       ← Dense vector CRUD + metadata filter
│   ├── bm25_store.py         ← Elasticsearch BM25 wrapper
│   └── schema.py             ← Shared document/chunk schema (Pydantic)
│
├── retrieval/                ← Phase 2: Query → candidate chunks
│   ├── dense_retriever.py    ← BGE-M3 query embedding + Qdrant search
│   ├── sparse_retriever.py   ← BM25 query + Elasticsearch search
│   ├── hybrid_retriever.py   ← RRF fusion of dense + sparse
│   ├── reranker.py           ← Cross-encoder reranking
│   └── query_decomposer.py   ← Multi-hop query decomposition
│
├── generation/               ← Phase 3: Context → answer
│   ├── generator.py          ← vLLM/llama.cpp inference wrapper
│   ├── citation_formatter.py ← Constrained citation output (Outlines)
│   ├── faithfulness_gate.py  ← DeBERTa-v3 NLI entailment check
│   └── uncertainty.py        ← Token entropy → confidence signal
│
├── serving/                  ← Phase 4: API + caching
│   ├── app.py                ← FastAPI application
│   ├── routes/
│   │   ├── query.py          ← POST /query
│   │   ├── ingest.py         ← POST /ingest
│   │   └── health.py         ← GET /health, GET /metrics
│   ├── cache.py              ← Redis semantic cache
│   └── middleware.py         ← Auth, rate limiting, logging
│
├── eval/                     ← Evaluation harness (runs throughout)
│   ├── dataset/
│   │   ├── qa_pairs.json     ← 200 hand-labeled QA pairs
│   │   └── schema.md         ← QA pair format documentation
│   ├── metrics.py            ← MRR@K, NDCG@5, faithfulness, BERTScore
│   ├── run_eval.py           ← CLI eval runner
│   └── results/              ← Timestamped eval snapshots (git-tracked)
│
├── observability/            ← Phase 4: Monitoring
│   ├── langfuse_client.py    ← Trace logging wrapper
│   └── prometheus_metrics.py ← Custom metrics definitions
│
├── frontend/                 ← Phase 5: Next.js UI
│   └── ...                   ← Standard Next.js structure
│
├── infra/
│   ├── docker-compose.yml    ← Local full-stack (all services)
│   ├── docker-compose.dev.yml← Dev override (hot reload)
│   └── modal_deploy.py       ← Modal Labs GPU inference deployment
│
├── docs/
│   ├── ablation.md           ← Living ablation table (updated each phase)
│   ├── failures.md           ← Failure log with root cause + fix
│   ├── decisions.md          ← Architecture Decision Records (ADRs)
│   └── diagrams/             ← Mermaid source files
│
├── scripts/
│   ├── download_corpus.sh    ← Fetch EDGAR + court opinions + EU AI Act
│   ├── seed_eval.py          ← Bootstrap eval set from corpus
│   └── benchmark_chunking.py ← Standalone chunking comparison experiment
│
├── tests/
│   ├── unit/                 ← Per-component unit tests
│   ├── integration/          ← End-to-end pipeline tests
│   └── conftest.py           ← Shared fixtures
│
├── pyproject.toml            ← Single source of truth for deps + tooling
├── .env.example              ← All required env vars, no values
└── .github/
    └── workflows/
        ├── eval_gate.yml     ← CI: block PR if faithfulness drops > 2%
        └── lint.yml          ← Ruff + mypy on every push
```

---

## 2. Schema Conventions

Every document chunk flowing through the system must conform to this schema.
Defined once in `indexing/schema.py`. Never duplicated.

```python
# indexing/schema.py
from pydantic import BaseModel, Field
from datetime import date
from typing import Literal, Optional

class ChunkMetadata(BaseModel):
    doc_id: str                          # SHA256 of source file path
    source_path: str                     # Original file path
    doc_type: Literal[
        "sec_filing", "court_opinion",
        "regulation", "contract"
    ]
    jurisdiction: Optional[str] = None  # e.g. "US-DE", "EU"
    doc_date: Optional[date] = None
    page_num: int
    section_title: Optional[str] = None
    chunk_index: int                    # Position within document
    total_chunks: int

class Chunk(BaseModel):
    chunk_id: str                       # f"{doc_id}_{chunk_index}"
    text: str
    metadata: ChunkMetadata
    embedding: Optional[list[float]] = None  # Populated after embedding

class QAPair(BaseModel):
    question_id: str
    question: str
    gold_answer: str
    gold_chunk_ids: list[str]           # Ground truth retrieval targets
    difficulty: Literal[
        "factoid", "multi_hop",
        "unanswerable", "temporal"
    ]
    notes: Optional[str] = None
```

**Rule:** If a function receives a chunk, it receives a `Chunk`. Not a dict.
Not a string. Not a tuple. Always `Chunk`.

---

## 3. Component Implementation Rules

### 3.1 Ingestion

**Parser (`ingestion/parser.py`)**
- Use `docling` as primary parser. Fallback to `pymupdf` if docling fails.
- Always extract: page number, section headers (from PDF outline or heuristic
  heading detection), raw text per page.
- Output: `list[dict]` of `{page, section, text}` — raw, before chunking.
- Never apply any text cleaning in the parser. Cleaning is the chunker's job.

**Chunker (`ingestion/chunker.py`)**
- Default strategy: **semantic chunking**.
  - Embed sentences with `sentence-transformers/all-MiniLM-L6-v2` (fast, cheap).
  - Compute cosine similarity between adjacent sentences.
  - Split where similarity drops below threshold (default: 0.75).
  - Merge splits smaller than `MIN_CHUNK_TOKENS=128` with neighbor.
  - Hard cap: `MAX_CHUNK_TOKENS=512`.
- Always implement `FixedSizeChunker` as well (baseline for ablation).
- Both chunkers must implement the same interface:
  ```python
  def chunk(self, pages: list[dict]) -> list[Chunk]: ...
  ```
- **Boundary artifact check:** Log a warning if any chunk starts with a
  lowercase letter (likely a mid-sentence split).

**Deduplicator (`ingestion/deduplicator.py`)**
- Use `datasketch` MinHash LSH.
- Threshold: Jaccard similarity > 0.85 → duplicate → skip.
- Log dedup stats: total seen, total skipped, ratio.

**Embedder (`ingestion/embedder.py`)**
- Model: `BAAI/bge-m3` via `sentence-transformers`.
- Always batch embed. Never embed one chunk at a time in a loop.
- Default batch size: 32. Configurable via env `EMBED_BATCH_SIZE`.
- Normalize embeddings before storage (Qdrant expects unit vectors for
  cosine similarity).

### 3.2 Indexing

**Qdrant Store (`indexing/qdrant_store.py`)**
- Collection name: `lexrag_chunks`.
- Vector config: `size=1024, distance=Cosine` (BGE-M3 output dim).
- Payload fields indexed for filtering: `doc_type`, `jurisdiction`,
  `doc_date`, `doc_id`.
- Always upsert, never insert. Re-ingesting a document must be idempotent.
- Sparse vectors stored in same collection (Qdrant native sparse support)
  to avoid dual-index sync issues.

**BM25 Store (`indexing/bm25_store.py`)**
- Index name: `lexrag_bm25`.
- Fields: `chunk_id` (keyword), `text` (text, English analyzer),
  `doc_type` (keyword), `jurisdiction` (keyword).
- Always sync `chunk_id` between Qdrant and Elasticsearch — this is the
  join key when fusing results.

### 3.3 Retrieval

**Hybrid Retriever (`retrieval/hybrid_retriever.py`)**

RRF formula:
```
score(chunk) = Σ 1 / (k + rank_i(chunk))
```
where `k=60` (standard RRF constant) and `rank_i` is the rank from
retriever `i`.

Default alpha weighting: `α=0.7` (dense weight in score combination).
This is a configurable hyperparameter — expose as `RETRIEVAL_ALPHA` env var.
The ablation in `docs/ablation.md` documents how this value was chosen.

**Re-ranker (`retrieval/reranker.py`)**
- Model: `cross-encoder/ms-marco-MiniLM-L-12-v2`.
- Re-rank top `N=20` candidates from hybrid retriever.
- Return top `K=5` after re-ranking (configurable: `RERANK_TOP_K`).
- Log re-rank score distribution per query to LangFuse.

**Query Decomposer (`retrieval/query_decomposer.py`)**
- Only activate for queries classified as multi-hop.
- Multi-hop classifier: simple heuristic first (check for conjunctions:
  "and", "if", "when", "after" combined with conditional structure).
  If heuristic fires → decompose. Log classification decision.
- Decomposition: call LLM with structured prompt to split into ≤3
  sub-queries. Each sub-query retrieved independently, results merged
  before re-ranking.
- **Never** run decomposition on every query. It adds 400ms+.

### 3.4 Generation

**Generator (`generation/generator.py`)**
- Model: `Qwen/Qwen2.5-7B-Instruct` (quantized: AWQ 4-bit for GPU,
  `llama-cpp-python` Q4_K_M for CPU).
- Always stream. Never block for full response.
- Context window budget: 4096 tokens. Allocate:
  - System prompt: ~200 tokens (fixed)
  - Retrieved context: ~3000 tokens (variable, trim from bottom if over)
  - Question + answer: ~800 tokens
- If context exceeds budget: trim lowest-scoring chunks first.

**Citation Formatter (`generation/citation_formatter.py`)**
- Use `outlines` library for constrained decoding.
- Output format enforced:
  ```
  <answer>
  [CLAIM] {claim_text} [SOURCE: {chunk_id}, p.{page_num}]
  ...
  </answer>
  ```
- Every factual sentence in the answer must have a `[SOURCE: ...]` tag.
- If the model cannot attach a source to a claim → the claim must not
  appear. This is enforced by the constrained grammar, not by post-hoc
  filtering.

**Faithfulness Gate (`generation/faithfulness_gate.py`)**
- Model: `cross-encoder/nli-deberta-v3-base`.
- For each `[CLAIM]` in the answer: run NLI against its cited `chunk_id`.
- NLI labels: entailment / neutral / contradiction.
- Gate logic:
  - If any claim is `contradiction` → reject entire answer, return abstention.
  - If > 30% of claims are `neutral` → flag as low-confidence.
  - Otherwise → pass.
- Abstention response format:
  ```json
  {
    "answer": null,
    "abstained": true,
    "reason": "Could not find sufficient grounding for this question.",
    "retrieved_chunks": [...]
  }
  ```

**Uncertainty (`generation/uncertainty.py`)**
- Compute mean token log-probability of the generated answer.
- Map to confidence bucket: High (> -0.3), Medium (-0.3 to -0.8), Low (< -0.8).
- Attach confidence bucket to every response. Surface in API response and UI.

### 3.5 Serving

**FastAPI App (`serving/app.py`)**
- Lifespan: load models on startup, release on shutdown.
- Never load models inside request handlers.
- All heavy objects (embedder, reranker, NLI model) stored as app state.

**Query Endpoint (`serving/routes/query.py`)**

Request:
```json
{
  "question": "string",
  "filters": {
    "doc_type": "sec_filing | court_opinion | regulation | contract",
    "jurisdiction": "string (optional)",
    "date_from": "YYYY-MM-DD (optional)",
    "date_to": "YYYY-MM-DD (optional)"
  },
  "stream": true
}
```

Response (non-streaming):
```json
{
  "answer": "string | null",
  "abstained": false,
  "confidence": "high | medium | low",
  "citations": [
    {
      "chunk_id": "string",
      "doc_id": "string",
      "page_num": 4,
      "section_title": "string",
      "excerpt": "string (first 200 chars of chunk)"
    }
  ],
  "latency_ms": {
    "retrieval": 180,
    "rerank": 120,
    "generation": 480,
    "total": 780
  },
  "trace_id": "langfuse trace id"
}
```

**Semantic Cache (`serving/cache.py`)**
- Backend: Redis (Upstash in prod, local Redis in dev).
- Key: embed the question, find nearest cached question via cosine similarity
  (store embeddings in Redis with `redis-py` + numpy).
- Cache hit threshold: cosine similarity > 0.95.
- TTL: 24 hours.
- Never cache abstentions.
- Log cache hit/miss ratio to Prometheus.

---

## 4. Evaluation Rules

### 4.1 QA Pair Format

```json
{
  "question_id": "q_001",
  "question": "What is the liability cap under Section 12.3 if the breach occurs post-warranty?",
  "gold_answer": "The liability cap is limited to the fees paid in the 12 months preceding the breach.",
  "gold_chunk_ids": ["abc123_14", "abc123_15"],
  "difficulty": "multi_hop",
  "doc_id": "abc123",
  "notes": "Requires linking Section 12.3 with warranty period definition in Section 4.1"
}
```

### 4.2 Metrics Implementation

All metrics in `eval/metrics.py`. Functions must be pure — no side effects.

| Metric | Function | Input |
|---|---|---|
| MRR@K | `mrr_at_k(retrieved_ids, gold_ids, k)` | lists |
| NDCG@5 | `ndcg_at_k(retrieved_ids, gold_ids, k=5)` | lists |
| Recall@10 | `recall_at_k(retrieved_ids, gold_ids, k=10)` | lists |
| Faithfulness | `faithfulness_score(answer, chunks)` | str, list[Chunk] |
| BERTScore F1 | `bertscore_f1(generated, gold)` | str, str |
| Citation Acc | `citation_accuracy(citations, chunks)` | list, list[Chunk] |

### 4.3 Eval Runner

```bash
# Run full eval
python eval/run_eval.py --split full --output eval/results/

# Run quick eval (50 questions, used in CI)
python eval/run_eval.py --split ci --output eval/results/

# Compare two snapshots
python eval/run_eval.py --compare eval/results/phase1.json eval/results/phase2.json
```

Output: timestamped JSON + human-readable markdown table written to
`eval/results/YYYY-MM-DD_HHMMSS.json`.

### 4.4 CI Eval Gate

`.github/workflows/eval_gate.yml` runs the CI split (50 questions) on every PR.
Gate conditions — PR is blocked if:
- Faithfulness drops more than 2 percentage points vs. `main`
- MRR@5 drops more than 3 percentage points vs. `main`
- P95 latency increases more than 500ms vs. `main`

Baseline stored in `eval/results/baseline.json` — updated manually after
each phase is complete and merged.

---

## 5. Logging + Observability

### 5.1 What to Log

Every query must produce a LangFuse trace containing:
- Input question + filters
- Sub-queries (if decomposed)
- Retrieved chunk IDs + scores (pre and post rerank)
- Faithfulness gate decision + per-claim NLI scores
- Final answer or abstention reason
- Confidence bucket
- Full latency breakdown

Use `observability/langfuse_client.py` wrapper. Never import LangFuse
directly in component files — always go through the wrapper.

### 5.2 Prometheus Metrics

Defined in `observability/prometheus_metrics.py`:

```python
# All metric names prefixed with lexrag_
lexrag_query_total          # Counter, labels: [status, confidence, difficulty]
lexrag_query_latency_ms     # Histogram, labels: [stage]  # retrieval/rerank/gen/total
lexrag_cache_hits_total     # Counter, labels: [hit/miss]
lexrag_abstention_total     # Counter, labels: [reason]
lexrag_faithfulness_score   # Gauge (rolling 100-query average)
```

Exposed at `GET /metrics` in Prometheus text format.

---

## 6. Environment Variables

All config via environment. Never hardcode. Full list in `.env.example`.

```bash
# Models
EMBED_MODEL=BAAI/bge-m3
RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-12-v2
NLI_MODEL=cross-encoder/nli-deberta-v3-base
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct

# Infrastructure
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
ELASTICSEARCH_URL=http://localhost:9200
REDIS_URL=redis://localhost:6379
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com

# Retrieval hyperparameters
RETRIEVAL_ALPHA=0.7
RERANK_TOP_K=5
RETRIEVAL_TOP_N=20
MIN_CHUNK_TOKENS=128
MAX_CHUNK_TOKENS=512
SEMANTIC_CHUNK_THRESHOLD=0.75
EMBED_BATCH_SIZE=32

# Faithfulness gate
FAITHFULNESS_CONTRADICTION_THRESHOLD=0
FAITHFULNESS_NEUTRAL_RATIO_THRESHOLD=0.3

# Cache
CACHE_SIMILARITY_THRESHOLD=0.95
CACHE_TTL_SECONDS=86400

# API
API_SECRET_KEY=
RATE_LIMIT_PER_MINUTE=30
```

---

## 7. Dependency Management

Single `pyproject.toml`. No `requirements.txt`.

```toml
[tool.ruff]
line-length = 88
select = ["E", "F", "I"]

[tool.mypy]
strict = false
ignore_missing_imports = true
```

Run before every commit:
```bash
ruff check . && mypy ingestion/ retrieval/ generation/ serving/
```

Both must pass clean. No exceptions.

---

## 8. Documentation Rules

### Architecture Decision Records (`docs/decisions.md`)

Every non-obvious design choice gets an ADR entry:

```markdown
## ADR-001: Semantic chunking over fixed-size

**Date:** YYYY-MM-DD
**Status:** Accepted

**Context:** Legal documents have variable-length clauses. Fixed-size chunking
produces boundary artifacts that degrade retrieval.

**Decision:** Use cosine similarity boundary detection for chunking.

**Consequences:** +15% MRR@5, +13% faithfulness. 2x ingestion time.
Acceptable tradeoff for this domain.

**Evidence:** See eval/results/phase1_chunking_ablation.json
```

### Failure Log (`docs/failures.md`)

```markdown
## FAIL-001: Multi-hop Delaware jurisdiction hallucination

**Date:** YYYY-MM-DD
**Query:** "What is the liability cap if the breach occurs post-warranty
and governing law is Delaware?"
**Symptom:** Correct document retrieved, wrong clause cited.
**Root cause:** Single-query retrieval conflated liability cap clause with
Delaware governing law clause in adjacent section.
**Fix:** Query decomposition into 3 sub-queries.
**Metric impact:** Multi-hop MRR@5: 0.51 → 0.74
```

---

## 9. Quick Reference

```bash
# Start full local stack
docker compose up -d

# Run ingestion on sample corpus (100 docs)
python ingestion/pipeline.py --input data/sample/ --limit 100

# Run single query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the liability cap in contract X?", "stream": false}'

# Run eval
python eval/run_eval.py --split ci

# Check metrics
curl http://localhost:8000/metrics

# View traces
open http://localhost:3001  # LangFuse local
```
