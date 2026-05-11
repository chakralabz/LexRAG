## ADR-000: Core Schema as Single Source of Truth

**Date:** 2026-04-14
**Status:** Accepted

**Context:** Multiple pipeline stages (ingestion, retrieval, generation, eval)
operate on the same chunk and QA objects. Duplicated shape definitions create
schema drift and brittle adapters.

**Decision:** Define `ChunkMetadata`, `Chunk`, and `QAPair` once in
`indexing/schema.py` and import across modules.

**Consequences:**
- Consistent validation and typing across the codebase.
- Faster onboarding because interfaces are centralized.
- Slight coupling to Pydantic model evolution, which is acceptable.

**Evidence:** Phase 0 bootstrap test coverage in `tests/unit/test_schema.py`.

## ADR-001: Initial Public Corpus Sources

**Date:** 2026-04-14
**Status:** Accepted

**Context:** We need a legally usable starter corpus that covers company
filings, regulation text, and court opinions without committing raw data.

**Decision:** Use scripted downloads into `data/raw/` from three public
sources: SEC EDGAR API, EUR-Lex EU AI Act PDF, and CourtListener API.

**Consequences:**
- Reproducible corpus bootstrap from source-of-truth endpoints.
- No large binary/data payloads committed to git.
- Some endpoint rate limits and occasional transient failures are expected.

**Evidence:** `scripts/download_corpus.sh` logs total files, failures, and size.
