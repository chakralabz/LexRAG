# 🧠 LEXRAG — Production-Grade Ingestion + Retrieval Architecture

> **A complete, auditable, enterprise-ready RAG pipeline** — from raw document upload to grounded LLM answer generation.

---

## 📋 Table of Contents

1. [High-Level System Flow](#1-high-level-system-flow)
2. [File Ingestion Layer](#2-file-ingestion-layer)
3. [Parsing Layer](#3-parsing-layer)
4. [Block Normalization Layer](#4-block-normalization-layer)
5. [Deduplication Layer](#5-deduplication-layer)
6. [Block Quality Validation](#6-block-quality-validation)
7. [Semantic Planning & Chunking](#7-semantic-planning--chunking)
8. [Chunk Post-Processing](#8-chunk-post-processing)
9. [Embedding Preparation Layer](#9-embedding-preparation-layer)
10. [Embedding Generation](#10-embedding-generation)
11. [Vector-Level Deduplication](#11-vector-level-deduplication)
12. [Vector DB Upsert & Index Optimization](#12-vector-db-upsert--index-optimization)
13. [Retrieval Layer](#13-retrieval-layer)
14. [Reranking](#14-reranking)
15. [Citation Resolution](#15-citation-resolution)
16. [LLM Context Builder](#16-llm-context-builder)
17. [Generation Layer](#17-generation-layer)
18. [Re-Index Strategy](#18-re-index-strategy)
19. [Audit Strategy](#19-audit-strategy)
20. [Observability & Monitoring](#20-observability--monitoring)

---

## 1. High-Level System Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        UPLOAD SOURCE                                │
│              (API upload / UI upload / batch ingest)                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │      File Validation Layer        │  ◄── MIME check, size limits,
            │  (virus scan, format allowlist)   │       extension validation
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │      File Type Detection          │  ◄── MIME sniffing + magic bytes
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │    Parser Selection Strategy      │  ◄── scanned vs native, encrypted,
            └──────────────────┬───────────────┘       image-heavy detection
                               │
                               ▼
            ┌──────────────────────────────────┐
            │    Primary Parser (Docling)       │
            └──────────────────┬───────────────┘
                               │ [on failure]
                               ▼
            ┌──────────────────────────────────┐
            │      Fallback Parser Chain        │
            │  1. PyMuPDF                       │
            │  2. Unstructured                  │
            │  3. OCR-only pipeline             │
            │  4. Manual recovery mode          │
            └──────────────────┬───────────────┘
                               │
                               ▼
                         ParsedBlock
                               │
                               ▼
            ┌──────────────────────────────────┐
            │    Block Normalization Layer      │
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │      Deduplication Layer          │
            │   (block-level)                   │
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │    Block Quality Validator        │
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │  BlockAwareSemanticPlanner        │
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │        ChunkBuilder               │
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │      ChunkModelFactory            │  ◄── resolves schema, chunk type
            └──────────────────┬───────────────┘
                               │
                               ▼
                            Chunk
                               │
                               ▼
            ┌──────────────────────────────────┐
            │     Chunk Post-Processor          │
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │  Embedding Preparation Layer      │
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │       Embedding Model             │  ◄── e.g. text-embedding-3-large,
            └──────────────────┬───────────────┘       BGE-M3, Cohere Embed v3
                               │
                               ▼
                         Vector Object
                    ┌─────────────────────┐
                    │  chunk              │
                    │  dense_embedding    │
                    │  sparse_embedding   │  ◄── NEW: for hybrid search
                    │  searchable metadata│
                    │  retrieval filters  │
                    └──────────┬──────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │  Vector-Level Deduplication       │
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │      Vector DB Upsert             │
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │   Index Optimization Layer        │
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │       Retrieval Layer             │  ◄── hybrid (dense + sparse)
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │          Reranker                 │  ◄── cross-encoder reranking
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │      Citation Resolver            │
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │     LLM Context Builder           │
            └──────────────────┬───────────────┘
                               │
                               ▼
            ┌──────────────────────────────────┐
            │      Generation Layer             │
            └──────────────────┬───────────────┘
                               │
                               ▼
                       ✅ Final Answer
```

---

## 2. File Ingestion Layer

### 🟡 2.1 File Validation Layer

> **Purpose:** Reject unsafe, malformed, or unsupported files before any parsing begins.

**Responsibilities:**
- MIME type verification (magic bytes, not just extension)
- File size enforcement (per-document and per-batch limits)
- Extension allowlisting
- Antivirus / malware scan hook
- Encrypted PDF detection (password-protected)
- Corrupt file detection (truncated ZIPs, malformed headers)
- Multi-file batch deduplication (reject re-uploads of identical file hashes)

**Failure Modes:**
- Extension spoofing bypasses MIME validation (mitigate: always check magic bytes)
- Encrypted PDFs silently produce zero content (mitigate: detect and reject early)
- Zero-byte files pass validation silently (mitigate: enforce minimum size threshold)

**Outputs:** Validated raw file → Parser Selection Strategy

---

### 🟡 2.2 File Type Detection

> **Purpose:** Accurately classify file format to route to the correct parser.

**Method:**
- Primary: `python-magic` (libmagic) for byte-level MIME detection
- Secondary: file extension cross-validation
- Tertiary: content heuristics (e.g. PDF header `%PDF-1.x`)

**Supported Types (production baseline):**

| Format | Detection Method | Notes |
|--------|-----------------|-------|
| PDF (native) | Magic bytes + text layer check | Must distinguish from scanned |
| PDF (scanned) | Text layer absence + image density | Routes to OCR pipeline |
| DOCX / XLSX / PPTX | ZIP magic bytes + OOXML content types | Office Open XML |
| HTML / XML | MIME + tag presence | Requires link stripping |
| TXT / MD | UTF-8/ASCII detection | Encoding detection required |
| Images (PNG/JPG/TIFF) | Magic bytes | Direct OCR path |
| Email (EML/MSG) | Header detection | Attachment extraction needed |

> ⚠️ **Correctness Note:** The original document skipped HTML, email, and image formats. Production systems must handle these explicitly, as they are common in enterprise legal and compliance contexts.

---

## 3. Parsing Layer

### 🔵 3.1 Parser Selection Strategy

> **Purpose:** Select the safest, highest-fidelity parser for a given document while preserving auditability and deterministic fallback behavior.

**Decision Logic:**

```
Is file encrypted?
  └─► YES → Reject / flag for manual decryption
  └─► NO → Continue

Is file a scanned PDF? (no text layer OR text layer < 50 chars/page avg)
  └─► YES → Route to OCR-only pipeline
  └─► NO → Continue

Is file image-heavy? (>60% page area covered by images, minimal text)
  └─► YES → Mixed OCR + native parse mode
  └─► NO → Native parse mode

Is format natively supported by Docling?
  └─► YES → Route to Docling (primary)
  └─► NO → Route to appropriate secondary parser
```

**Parser Confidence Scoring:**

| Signal | Weight |
|--------|--------|
| Native text layer present | +0.4 |
| Tables detected and structured | +0.2 |
| Heading hierarchy preserved | +0.2 |
| OCR required | −0.3 |
| Fallback parser used | −0.2 |
| Manual recovery required | −0.5 |

**Metadata Emitted:**
```json
{
  "parser_used": "docling",
  "fallback_used": false,
  "ocr_used": false,
  "parse_confidence": 0.91,
  "scanned_pdf": false,
  "encrypted": false
}
```

---

### 🔵 3.2 Fallback Parser Chain

> **Purpose:** Guarantee document ingestion even when the primary parser fails. No document should be silently dropped.

**Chain Order:**

```
[1] Docling          ← Primary (layout-aware, table-aware, heading-aware)
      │ FAIL
      ▼
[2] PyMuPDF          ← Fast, reliable for text-heavy native PDFs
      │ FAIL
      ▼
[3] Unstructured     ← Broad format support, lower fidelity
      │ FAIL
      ▼
[4] OCR-only (Tesseract / AWS Textract / Azure DI)
      │ FAIL
      ▼
[5] Manual Recovery  ← Alert ops team, quarantine document, partial extraction if possible
```

> ⚠️ **Correctness Note:** The original document did not specify OCR engines. In production, specify the OCR provider: Tesseract (open source), AWS Textract (cloud, higher accuracy, handles tables), or Azure Document Intelligence. The choice affects latency, cost, and quality significantly.

**Responsibilities:**
- Track `fallback_used`, `fallback_reason`, `parser_used` per block
- Degrade `parse_confidence` at each fallback step
- Support partial extraction (extract what succeeded, flag what failed)
- Never silently drop a document — always emit a status event

**Failure Modes & Recovery:**

| Failure | Recovery |
|---------|----------|
| Binary garbage extraction | Discard block, flag parser anomaly |
| Duplicate content generation | Block-level dedup catches downstream |
| OCR hallucination | Low-confidence block filtering removes |
| Partial document truncation | `partial_extraction: true` flag emitted |

---

## 4. Block Normalization Layer

> **Purpose:** Convert raw parser output into retrieval-safe, canonical blocks. Inconsistent raw output is the primary source of downstream retrieval degradation.

### 🟢 Subsystems

| Subsystem | Responsibility |
|-----------|---------------|
| `TextNormalizer` | Whitespace normalization, control character removal, encoding repair |
| `HeadingNormalizer` | Normalize heading levels, detect false headings (ALL CAPS paragraphs, bold short lines) |
| `SectionPathNormalizer` | Build `section_path` lineage: `["Part I", "Section 3", "3.2 Definitions"]` |
| `CodeBlockNormalizer` | Detect and preserve code fencing, indentation, language tags |
| `TableNormalizer` | Recover table structure, fill missing cells, detect merged cells |
| `OCRNormalizer` | Character substitution repair, word boundary correction, confidence gating |
| `ParserArtifactCleaner` | Remove page numbers embedded in text, watermarks, print artifacts |
| `MetadataEnricher` | Attach `page_number`, `document_section`, `block_type`, `block_index` |

### 🟢 Critical Correctness Notes

> ⚠️ **Legal text protection:** Legal documents often contain intentional repeated clauses (e.g., identical indemnification language in multiple schedules). The `ParserArtifactCleaner` must **not** aggressively remove repetition in legal contexts. Use document-type-aware cleaning policies.

> ⚠️ **OCR over-cleaning:** Aggressively cleaning OCR output can destroy valid legal terms (e.g., "§", "¶", "—"). Protect legal symbols and punctuation from over-normalization.

> ⚠️ **Heading detection:** Not all bold short lines are headings. Do not auto-promote text to headings based on formatting alone without contextual validation.

### 🟢 Protected Block Types

Some blocks must bypass or receive minimal normalization:

```
PROTECTED:
  - code_block       → preserve formatting exactly
  - legal_citation   → preserve punctuation and symbols
  - table            → preserve structure, never flatten to prose
  - math_formula     → preserve LaTeX or MathML
```

**Metadata Emitted:**
```json
{
  "block_type": "paragraph",
  "section_path": ["Part I", "Definitions"],
  "heading_anchor": "section-1-2-definitions",
  "page_number": 4,
  "ocr_confidence": null,
  "normalized": true,
  "protected": false
}
```

---

## 5. Deduplication Layer

> **Purpose:** Remove duplicate, near-duplicate, and low-value repeated content **without deleting legally relevant repetition**.

### 🟣 Block-Level Deduplication

**Methods:**

| Method | Technique | Threshold |
|--------|-----------|-----------|
| Exact duplicate | SHA-256 hash | Identical hash → drop |
| Near-duplicate | MinHash / SimHash | Jaccard > 0.95 → review |
| Repeated headers/footers | Page-position + text pattern | Seen on >3 pages → suppress |
| Boilerplate | TF-IDF anomaly / known pattern list | Low uniqueness → drop |
| OCR duplicate regions | Bounding box overlap + text similarity | Overlap + sim > 0.9 → drop |

### 🟣 Legal-Sensitive Bypass Rules

> ⚠️ **Critical:** In legal RAG systems, identical clauses across multiple contract schedules are **intentional and legally distinct in context**. Implement a `legal_sensitive_bypass` policy:

```
IF document_type IN ["contract", "legislation", "regulation"]
  AND block_type IN ["clause", "section"]
  AND dedup_confidence < 0.99
  THEN → PRESERVE (do not deduplicate)
```

**Metadata Emitted:**
```json
{
  "dedup_status": "kept",
  "dedup_method": null,
  "near_duplicate_of": null,
  "dedup_bypass_reason": "legal_sensitive"
}
```

---

## 6. Block Quality Validation

> **Purpose:** Catch low-quality, malformed, or junk blocks before they enter chunking and pollute the vector index.

### 🔴 Validation Checks

| Check | Condition | Action |
|-------|-----------|--------|
| Empty block | `len(text.strip()) == 0` | Drop |
| Micro block | `token_count < 5` | Drop unless heading |
| Low OCR confidence | `ocr_confidence < 0.6` | Flag + soft drop |
| Malformed table | Column count inconsistent across rows | Attempt repair → flag |
| Junk text | High symbol ratio, encoding artifacts | Drop |
| Parser anomaly | Implausible character distributions | Flag for review |
| Truncated block | Block ends mid-sentence + is last in page | Attempt merge with next page |
| Duplicate of dropped block | Hash match to known-dropped content | Drop |

> ⚠️ **Correctness Note:** The original document listed "parser anomaly detection" but did not specify detection logic. In practice, this is implemented via character entropy analysis, symbol-to-word ratios, and implausible n-gram patterns.

**Metadata Emitted:**
```json
{
  "quality_status": "passed",
  "quality_flags": [],
  "drop_reason": null,
  "ocr_confidence": 0.87
}
```

---

## 7. Semantic Planning & Chunking

### 🟠 7.1 BlockAwareSemanticPlanner

> **Purpose:** Analyze block structure and semantics to inform optimal chunking strategy **before** ChunkBuilder executes. This is a planning pass, not a transformation pass.

**Responsibilities:**
- Identify section boundaries and heading anchors
- Classify block types: `paragraph`, `table`, `list`, `code`, `heading`, `caption`
- Score semantic coherence between adjacent blocks
- Mark blocks that must remain standalone (tables, code blocks, isolated definitions)
- Plan overlap regions (which blocks should be repeated across chunk boundaries)
- Assign chunking strategy per region: `semantic_merge`, `sliding_window`, `standalone`, `table_aware`

**Planner Output per Block:**
```json
{
  "chunking_strategy": "semantic_merge",
  "standalone": false,
  "merge_with_next": true,
  "overlap_candidate": true,
  "section_boundary": false,
  "heading_anchor": "section-3-liability"
}
```

---

### 🟠 7.2 ChunkBuilder

> **Purpose:** Create retrieval-safe, semantically coherent chunks from normalized blocks using the planner's strategy map.

**Chunking Strategies:**

| Strategy | When Used | Behavior |
|----------|-----------|----------|
| `semantic_merge` | Adjacent paragraphs in same section | Merge until token limit |
| `sliding_window` | Long sections without clear boundaries | Fixed window with overlap |
| `standalone` | Tables, code blocks, isolated definitions | Single block = single chunk |
| `table_aware` | Tables with surrounding context | Table + caption + intro sentence |
| `heading_anchored` | Content directly under a heading | Heading always included in chunk |

**Token Limits:**

```
MIN chunk size:  64 tokens   (below this → merge with neighbor)
TARGET size:     512 tokens  (optimal for most embedding models)
MAX size:        1024 tokens (hard cap — split regardless)
OVERLAP:         64–128 tokens (shared between adjacent chunks)
```

> ⚠️ **Correctness Note:** The original document did not specify token limits. These are critical — most embedding models have sequence limits (e.g., 512 tokens for older models, 8192 for newer ones). Chunk sizes must be validated against the specific embedding model in use.

**Responsibilities:**
- Enforce min/max token safety
- Preserve heading context (always include nearest heading in chunk)
- Never split mid-sentence or mid-clause
- Generate `overlap_prev` and `overlap_next` metadata
- Preserve `source_blocks` list (which normalized blocks composed this chunk)
- Preserve full `section_path` lineage in chunk metadata

---

### 🟠 7.3 ChunkModelFactory

> **Purpose:** Serialize chunks into the canonical `Chunk` schema with all required fields populated.

**Chunk Schema:**

```json
{
  "chunk_id": "doc_abc123_p4_b7_h2f9a",
  "document_id": "doc_abc123",
  "document_version": "v3",
  "text": "...",
  "embedding_text": "...",
  "chunk_type": "paragraph",
  "section_path": ["Part I", "Definitions"],
  "heading_anchor": "section-1-definitions",
  "page_start": 4,
  "page_end": 4,
  "token_count": 312,
  "source_blocks": ["block_041", "block_042"],
  "overlap_prev": "chunk_abc123_p4_b5",
  "overlap_next": "chunk_abc123_p4_b9",
  "chunking_strategy": "semantic_merge",
  "parser_used": "docling",
  "fallback_used": false,
  "ocr_used": false,
  "parse_confidence": 0.91,
  "chunk_quality_score": 0.88,
  "ingestion_timestamp": "2025-01-15T10:23:44Z"
}
```

---

## 8. Chunk Post-Processing

> **Purpose:** Validate, score, and enrich chunks before embedding preparation. Last chance to catch quality issues before the embedding layer.

### ✅ Post-Processing Steps

| Step | Description |
|------|-------------|
| **Overlap Validation** | Verify `overlap_prev`/`overlap_next` references exist and token counts are correct |
| **Citation Validation** | Detect citation patterns in text; validate page references are within document bounds |
| **Chunk Quality Scoring** | Score 0.0–1.0 based on: token count, heading presence, section coverage, parser confidence |
| **Reranker Metadata Enrichment** | Add fields for reranker: `doc_title`, `section_summary`, `block_type_distribution` |
| **Final Normalization** | Last whitespace/encoding cleanup pass before embedding |
| **Hallucination Risk Flagging** | Flag chunks with very low parse confidence or high OCR rate for downstream caution |

**Quality Score Formula (suggested):**
```
quality_score =
  (0.3 × parse_confidence)
  + (0.2 × heading_present)
  + (0.2 × token_count_in_range)
  + (0.15 × section_path_depth > 0)
  + (0.15 × no_ocr_used)
```

> Chunks with `quality_score < 0.4` should be flagged and optionally excluded from retrieval or marked with a low-confidence indicator in answers.

---

## 9. Embedding Preparation Layer

> **Purpose:** Prepare chunk content for embedding generation without losing retrieval relevance or citation precision.

### 📐 Embedding Text Construction

The `embedding_text` field is **distinct from** the raw `text` field. It is optimized for retrieval, not for display.

**Construction Rules:**

| Chunk Type | Embedding Text Strategy |
|------------|------------------------|
| Paragraph | `[HEADING: {heading}] {text}` |
| Table | `[TABLE: {caption}]\n{row1_key}: {row1_val}\n{row2_key}: {row2_val}...` |
| Code block | `[CODE: {language}]\n{code}` |
| List | `[SECTION: {heading}]\n- {item1}\n- {item2}...` |
| Definition | `[DEFINITION: {term}] {definition_text}` |

> ⚠️ **Correctness Note:** The original document mentioned "table serialization" and "metadata-aware embedding prep" but did not specify how. Row-by-row serialization of tables is standard practice and significantly improves table retrieval accuracy.

**Responsibilities:**
- Prepend section/heading context to embedding text
- Serialize tables into key-value or row-description format
- Preserve code language tags
- Strip display-only metadata (page numbers, parser provenance) from embedding text
- Validate embedding text length against model's max sequence length

---

## 10. Embedding Generation

> **Purpose:** Convert embedding_text into dense vector representations using a production embedding model.

### 🔷 Model Selection

| Model | Dim | Max Tokens | Best For |
|-------|-----|-----------|---------|
| `text-embedding-3-large` (OpenAI) | 3072 | 8191 | General English |
| `BGE-M3` (BAAI) | 1024 | 8192 | Multilingual, hybrid |
| `Cohere Embed v3` | 1024 | 512 | Classification-aware |
| `E5-mistral-7b` | 4096 | 32768 | Long context |

> ⚠️ **Correctness Note:** The original document did not name any embedding model. In production, the embedding model must be explicitly versioned and pinned. Changing the embedding model requires **full re-indexing** of all vectors — this is a critical operational risk.

### 🔷 Operational Requirements

- **Batching:** Send chunks in batches (e.g., 256 chunks per API call) for throughput
- **Retry logic:** Exponential backoff on rate limit errors
- **Version pinning:** Record `embedding_model` and `embedding_model_version` in vector metadata
- **Embedding caching:** Cache embeddings for identical `embedding_text` to avoid redundant API calls
- **Dimensionality consistency:** Validate embedding dimension matches index configuration on every upsert

---

## 11. Vector-Level Deduplication

> **Purpose:** Catch semantic near-duplicates that survived block-level deduplication — especially across document versions or closely related documents.

### 🟤 Methods

| Method | Technique | Threshold |
|--------|-----------|-----------|
| Cosine similarity check | Compare new vector against existing index | Similarity > 0.98 → flag |
| Version suppression | Same `doc_id` + `chunk_id` with new `doc_version` | Soft-delete old, upsert new |
| Cross-document near-duplicate | Similarity > 0.97 across different `doc_id` | Log, keep both (different provenance) |

> ⚠️ **Correctness Note:** Across different documents, near-identical vectors should generally **be kept** (both are valid sources with distinct citation provenance). Only suppress true duplicates within the same document lineage.

---

## 12. Vector DB Upsert & Index Optimization

### 💾 12.1 Vector DB Upsert

> **Purpose:** Persist chunks safely into vector storage with deterministic re-indexing and document version control.

**Re-Index Strategy:**

```
1. Compute deterministic chunk_id:
   chunk_id = hash(doc_id + page_number + block_hash + chunk_index)

2. On re-ingest of same document:
   a. Soft-delete all existing chunks with same doc_id + doc_version_old
   b. Upsert new chunks atomically
   c. Confirm all new chunks written before committing soft-delete

3. On failure mid-upsert:
   a. Roll back: restore soft-deleted chunks
   b. Emit alert + quarantine new batch
```

> ⚠️ **Correctness Note:** The original document's re-index strategy mentioned "no UUID-based chunk identity." This is correct — UUIDs generated at ingest time will differ on re-ingest, creating orphaned duplicates. Deterministic IDs based on content + position are required for safe re-indexing.

**Required Vector Metadata (filterable):**

```json
{
  "chunk_id": "...",
  "document_id": "...",
  "document_version": "...",
  "document_type": "contract",
  "section_path": ["Part I", "Definitions"],
  "page_start": 4,
  "chunk_type": "paragraph",
  "parser_used": "docling",
  "parse_confidence": 0.91,
  "chunk_quality_score": 0.88,
  "ingestion_timestamp": "2025-01-15T10:23:44Z",
  "embedding_model": "text-embedding-3-large",
  "embedding_model_version": "2024-04"
}
```

---

### 💾 12.2 Index Optimization Layer

> **Purpose:** Prepare the vector index for high-performance hybrid retrieval and reranking.

**Responsibilities:**

| Task | Description |
|------|-------------|
| Metadata indexes | Create filterable indexes on `doc_id`, `doc_type`, `page`, `chunk_type` |
| Dense index | HNSW or IVF-PQ for ANN search on dense embeddings |
| Sparse index | BM25 / SPLADE index on tokenized text for keyword retrieval |
| Hybrid search prep | Configure reciprocal rank fusion (RRF) or weighted score merge |
| Reranker metadata | Pre-compute fields needed by reranker (doc title, section label) |
| Payload optimization | Store only retrieval-necessary metadata in vector DB; keep full metadata in relational store |

---

## 13. Retrieval Layer

> **Purpose:** Retrieve the most relevant chunks for a given query using hybrid search.

### 🔍 Hybrid Retrieval Architecture

```
User Query
    │
    ├──── Dense Retrieval ────► ANN search (cosine similarity)
    │     (semantic)            top-k dense results
    │
    └──── Sparse Retrieval ───► BM25 / SPLADE keyword search
          (lexical)             top-k sparse results
                │
                ▼
        Score Fusion (RRF)
                │
                ▼
        Merged top-K candidates
```

> ⚠️ **Correctness Note:** The original document listed "hybrid search preparation" under index optimization but did not describe the retrieval query path. In production, hybrid retrieval (dense + sparse fusion) consistently outperforms dense-only retrieval, especially for legal and technical documents with precise terminology.

**Retrieval Filters (applied before scoring):**

```json
{
  "document_id": {"in": ["doc_abc", "doc_xyz"]},
  "document_type": {"eq": "contract"},
  "chunk_quality_score": {"gte": 0.4},
  "parse_confidence": {"gte": 0.5}
}
```

**Outputs:** Top-K candidate chunks with retrieval scores → Reranker

---

## 14. Reranking

> **Purpose:** Re-score retrieval candidates using a cross-encoder that considers query-chunk relevance jointly, not independently.

### 🏆 Cross-Encoder Reranking

| Model | Notes |
|-------|-------|
| `BAAI/bge-reranker-v2-m3` | Multilingual, strong on technical text |
| `Cohere Rerank 3` | API-based, high accuracy |
| `ms-marco-MiniLM-L-12-v2` | Fast, English-focused |

**Process:**

```
For each candidate chunk:
  input = [QUERY: {query}] [DOC: {chunk.embedding_text}]
  score = cross_encoder(input)  ← full attention over query+chunk jointly

Sort by cross-encoder score (descending)
Select top-N for context window
```

**Metadata Emitted:**
```json
{
  "reranker_score": 0.94,
  "retrieval_rank": 3,
  "reranker_rank": 1,
  "reranker_correction": true
}
```

> `reranker_correction: true` means the chunk was not in the top-3 retrieval results but was promoted to top-3 by reranking. Track this metric — high correction rates indicate retrieval quality issues.

---

## 15. Citation Resolution

> **Purpose:** Guarantee answer grounding and source traceability. Every claim in the final answer must be traceable to a specific source chunk and document location.

### 📎 Citation Resolution Process

```
1. For each chunk selected for context window:
   - Resolve: doc_id → document metadata (title, version, date)
   - Resolve: chunk_id → page_number, section_path, heading_anchor
   - Resolve: source_blocks → original block positions

2. Assign citation_id to each chunk (e.g., [1], [2], [3])

3. During generation, LLM is instructed to cite by citation_id inline

4. Post-generation: validate all cited citation_ids exist in context window
   - Uncited chunks → not used (log for coverage analysis)
   - Invalid citation_ids → hallucination detected → abstain or flag answer
```

> ⚠️ **Correctness Note:** The original document listed "hallucination prevention" as a responsibility of the Citation Resolver. This is partially correct — citation validation prevents **unsupported claims** but does not prevent all hallucinations (the LLM can still hallucinate within the supported text). Combine citation validation with answer faithfulness scoring for robust hallucination prevention.

**Citation Object:**
```json
{
  "citation_id": 1,
  "document_title": "Master Services Agreement v3",
  "document_id": "doc_abc123",
  "document_version": "v3",
  "page": 4,
  "section": "Part I, Section 1.2 — Definitions",
  "heading_anchor": "section-1-2-definitions",
  "chunk_id": "doc_abc123_p4_b7_h2f9a",
  "confidence": 0.91
}
```

---

## 16. LLM Context Builder

> **Purpose:** Construct safe, high-signal, citation-linked context windows for the generation layer.

### 🏗️ Context Construction Steps

```
1. RECEIVE top-N reranked chunks (post-reranker)

2. DEDUPLICATE context window:
   - Remove near-identical chunks (cosine > 0.98 within window)
   - Remove chunks from same block if overlap is >80%

3. ORDER chunks:
   - Group by document, then by section_path order
   - Interleave from different documents if multi-doc query
   - Place highest-reranker-score chunks first within each group

4. DETECT conflicts:
   - Flag chunks containing contradictory information (date, amount, clause)
   - Inject conflict warning into LLM prompt if detected

5. COMPRESS (if context window at risk of overflow):
   - Trim low-quality chunks first (lowest chunk_quality_score)
   - Never trim a chunk that is the sole source for a query term

6. FORMAT with citation IDs:
   [SOURCE 1 | doc: Master Services Agreement v3 | page 4 | Section 1.2]
   {chunk text}

   [SOURCE 2 | doc: Addendum B | page 12 | Section 4.1]
   {chunk text}

7. EMIT context_window metadata:
   - total_tokens
   - num_sources
   - num_documents
   - conflict_detected
   - context_quality_score
```

> ⚠️ **Correctness Note:** The original document did not include context compression or conflict detection logic. Both are essential in production — context overflow causes silent truncation, and contradictory clauses without conflict flagging lead to unreliable answers.

---

## 17. Generation Layer

> **Purpose:** Generate a grounded, citation-backed answer from the constructed context window.

### ⚡ Generation Process

```
SYSTEM PROMPT:
  - Role definition
  - Citation instruction: "Always cite sources using [N] format"
  - Abstention policy: "If the answer cannot be found in the provided sources, say so explicitly"
  - Conflict instruction: "If sources conflict, surface the conflict rather than resolving it"

USER PROMPT:
  - Query
  - Formatted context window (with citation IDs)

GENERATION:
  - Temperature: 0.0–0.2 (factual RAG tasks require low temperature)
  - Max tokens: context-dependent
  - Stream or batch depending on latency requirements

POST-GENERATION VALIDATION:
  - Citation ID validation (all cited IDs exist in context)
  - Faithfulness scoring (e.g., using NLI model or secondary LLM check)
  - Abstention detection (did model abstain when it should have answered?)
  - PII detection in output (if applicable)
```

> ⚠️ **Correctness Note:** The original document did not include a Generation Layer detail section. Post-generation validation (faithfulness scoring, citation validation) is a critical production requirement — especially in legal RAG where wrong answers can cause material harm.

---

## 18. Re-Index Strategy

> **Purpose:** Support safe, lossless, citation-preserving re-ingestion of updated document versions.

### ♻️ Re-Index Rules

| Rule | Rationale |
|------|-----------|
| Deterministic chunk IDs only | Enables safe upsert without orphan detection |
| ID formula: `hash(doc_id + page + block_hash + chunk_index)` | Stable across re-ingests if content unchanged |
| Version-aware upsert | New version → soft-delete old chunks → upsert new |
| Atomic replacement | New chunks must be confirmed written before old are deleted |
| Rollback path | If new ingest fails mid-way → restore from soft-delete |
| Citation preservation | Changed chunks get new IDs; existing citations to old IDs remain valid via citation archive |

### ♻️ Version-Change Scenarios

```
Scenario A: Minor edit (corrected typo on page 5)
  → Only affected chunks get new IDs
  → Unchanged chunks retain same IDs → no re-embedding needed

Scenario B: Document restructuring (sections reordered)
  → All chunk IDs change (page + block position changed)
  → Full re-embedding required

Scenario C: New document version uploaded
  → New doc_id + doc_version created
  → Previous version retained in archive (for citation continuity)
  → Retrieval filters updated to prefer latest version unless pinned
```

---

## 19. Audit Strategy

> **Purpose:** Provide enterprise auditability and legal defensibility for every ingested document and every generated answer.

### 📋 Required Metadata — Complete Field Set

| Field | Description | Source |
|-------|-------------|--------|
| `parser_used` | Which parser extracted the document | Parser layer |
| `fallback_used` | Whether fallback was triggered | Parser layer |
| `ocr_used` | Whether OCR was required | Parser layer |
| `parse_confidence` | 0.0–1.0 parser confidence score | Parser layer |
| `chunking_strategy` | Strategy used for this chunk | ChunkBuilder |
| `heading_anchor` | Section heading this chunk belongs to | SectionPathNormalizer |
| `overlap_prev` / `overlap_next` | Adjacent chunk IDs for overlap resolution | ChunkBuilder |
| `source_blocks` | Raw block IDs that compose this chunk | ChunkBuilder |
| `chunk_quality_score` | 0.0–1.0 chunk quality rating | Post-processor |
| `ingestion_timestamp` | ISO 8601 UTC timestamp | Ingestion pipeline |
| `document_version` | Version label of source document | Metadata store |
| `embedding_model` | Model name used for embedding | Embedding layer |
| `embedding_model_version` | Pinned version of embedding model | Embedding layer |
| `reranker_score` | Cross-encoder score at retrieval time | Reranker |
| `citation_confidence` | Citation resolver confidence | Citation resolver |

---

## 20. Observability & Monitoring

> **Purpose:** Provide production visibility into pipeline health, quality trends, and retrieval effectiveness.

### 📊 Metrics by Layer

#### Ingestion Metrics
```
parser_success_rate          → % docs parsed without fallback
parser_fallback_rate         → % docs requiring ≥1 fallback
ocr_activation_rate          → % docs requiring OCR
parse_confidence_p50/p95     → confidence distribution
file_type_failure_rate       → failures by file type
manual_recovery_rate         → % docs reaching manual recovery
```

#### Block Quality Metrics
```
block_drop_rate              → % blocks dropped by quality validator
ocr_cleanup_rate             → % blocks modified by OCR normalizer
artifact_removal_rate        → % blocks with parser artifacts cleaned
malformed_table_rate         → % tables requiring repair
dedup_drop_rate              → % blocks removed by deduplication
```

#### Chunking Metrics
```
avg_chunk_token_count        → should cluster near target (512)
chunk_quality_score_p50/p95  → quality score distribution
standalone_block_ratio       → % chunks that are standalone (table/code)
overlap_validation_failures  → % chunks with invalid overlap references
```

#### Embedding & Index Metrics
```
embedding_failure_rate       → % chunks where embedding failed
embedding_retry_rate         → % embeddings requiring retry
vector_duplicate_rate        → % vectors deduplicated at vector level
upsert_failure_rate          → % upserts failing
re_index_consistency_rate    → % re-indexes with zero orphaned chunks
```

#### Retrieval & Answer Quality Metrics
```
retrieval_hit_rate           → % queries returning ≥1 high-quality chunk
reranker_correction_rate     → % where reranker changed top-1 result
citation_success_rate        → % answers with all citations validated
orphan_citation_rate         → % cited IDs not found in context window
unsupported_answer_rate      → % answers where model should have abstained
faithfulness_score_p50       → NLI-based faithfulness distribution
```

### 📊 Alerting Thresholds (recommended)

| Metric | Warning | Critical |
|--------|---------|---------|
| `parser_fallback_rate` | > 15% | > 30% |
| `manual_recovery_rate` | > 2% | > 5% |
| `chunk_quality_score_p50` | < 0.6 | < 0.4 |
| `orphan_citation_rate` | > 1% | > 5% |
| `unsupported_answer_rate` | > 10% | > 25% |
| `upsert_failure_rate` | > 0.5% | > 2% |

---

## 🗺️ Pipeline Summary Cheatsheet

```
INGESTION
  File Validation → Type Detection → Parser Selection
  → Primary Parser (Docling)
  → Fallback Chain (PyMuPDF → Unstructured → OCR → Manual)
  → ParsedBlock

NORMALIZATION & QUALITY
  Block Normalization → Block Deduplication → Block Quality Validation

CHUNKING
  SemanticPlanner → ChunkBuilder → ChunkModelFactory
  → Chunk → Post-Processor

EMBEDDING
  Embedding Preparation → Embedding Model → Vector Object

INDEXING
  Vector Deduplication → Vector DB Upsert → Index Optimization

RETRIEVAL
  Hybrid Search (Dense + Sparse) → Reranker → Citation Resolver
  → LLM Context Builder → Generation → Final Answer
```

---

*Document Version: 2.0 | Last Updated: 2025 | Status: Production Reference*