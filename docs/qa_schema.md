# QAPair Dataset Schema

Each item in `data/arxiv/qa_pairs.json` or
`data/arxiv/testcases/qa_pairs_ci.json` follows this shape:

```json
{
  "question_id": "q_001",
  "question": "Which paper matches this abstract snippet about sparse retrieval?",
  "gold_answer": "Transformers for Sparse Search",
  "gold_chunk_ids": ["doc_abc123_14"],
  "gold_doc_ids": ["doc_abc123"],
  "difficulty": "factoid",
  "notes": "Optional annotation"
}
```

Allowed `difficulty` values:
- `factoid`
- `multi_hop`
- `unanswerable`
- `temporal`

`gold_doc_ids` is optional and useful for real-corpus evaluation when
ground-truth is annotated at document level. During eval, these are expanded to
chunk IDs after ingestion.

Policy:
- CI testcase files must stay lightweight (default: up to 10 questions).
- Do not add synthetic placeholder probes to active datasets.
