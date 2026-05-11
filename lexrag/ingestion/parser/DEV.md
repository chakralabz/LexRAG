# `lexrag.ingestion.parser` Developer Guide

This file is for developers working inside the `parser` package.
Its goal is to reduce the "where is this behavior coming from?" feeling when
you are navigating routing logic, fallback execution, OCR, and result shaping.

Use this guide together with
[README.md](/Users/ayushsolanki/Desktop/Projects/LexRAG/lexrag/ingestion/parser/README.md)
for the public package view.

## Why This Package Exists

This package turns a file that has already passed the file-ingestion boundary
into canonical parsed blocks plus a structured parse report.

It exists so the rest of the ingestion pipeline does not need to know:

- which backend was chosen
- why fallback happened
- whether OCR was involved
- how confidence and provenance were attached
- which parser attempts failed before one succeeded

This package should trust `lexrag.ingestion.file_ingestion` for path safety,
file validation, and type detection. If parser code starts duplicating those
concerns, the architecture gets muddy fast.

## Mental Model

Think of the parser package as four layers:

1. transition from `FileLoadResult` into parser execution
2. deterministic route selection
3. backend chain execution with structured attempts
4. provenance/confidence annotation of canonical parsed blocks

## Terminology

These names are easy to blur together, so this is the canonical meaning:

- `DocumentParser`: the orchestrator that parses one approved document
- `DocumentParseResult`: the actual parse output for that document
- `LoadedDocumentParserPipeline`
- `LoadedDocumentParseResult`
- `LoadedDocumentParseStatus`

Short version:

- "document parse" = the real parse payload
- "loaded-document parse" = the outer wrapper around a loaded file going
  through parsing

## Main Flow

```text
caller path
  -> FileLoadService
  -> FileLoadResult
  -> LoadedDocumentParserPipeline or DocumentParser.parse_with_report(...)
      -> ParserSelectionStrategy
      -> ParserBackendRegistry
      -> ParserChainExecutor
          -> DoclingParser
          -> PyMuPDFParser
          -> UnstructuredParser
          -> OCROnlyParser
          -> ManualRecoveryParser
      -> ParsedBlockFactory
      -> ParserProvenanceAnnotator
      -> ParseConfidenceScorer
  -> DocumentParseResult / LoadedDocumentParseResult
```

## Entry Points You Will Usually Touch

### `orchestration/document_parser.py`

- `DocumentParser`
- Main orchestrator for one document
- Use this when you want the full parser workflow including file-loader
  integration and structured `DocumentParseResult`

### `orchestration/loaded_document_parser_pipeline.py`

- `LoadedDocumentParserPipeline`
- Transition adapter from `FileLoadResult` to a terminal parser status
- Converts low-level parser exceptions into stable statuses like
  `parsed`, `rejected`, `failed`, and `quarantined`

### `orchestration/parser_selection_strategy.py`

- `ParserSelectionStrategy`
- Determines which backend order to try and why
- If a document is going down the wrong parse path, start here after checking
  file-type detection upstream

### `orchestration/parser_chain_executor.py`

- `ParserChainExecutor`
- Runs the chosen chain, records `ParseAttempt`s, and stops at the first
  non-empty success
- If fallback behavior feels wrong, inspect this file

### `orchestration/parser_provenance_annotator.py`

- `ParserProvenanceAnnotator`
- Attaches parser metadata and confidence to every final `ParsedBlock`
- Important whenever debugging downstream trust or auditability

## Package Map

### Top-level modules

| File | Main classes/functions | Why it exists |
| --- | --- | --- |
| `__init__.py` | exports, `parse_document()` | Stable public API surface and legacy compatibility helper. |
| `README.md` | package overview | Public-facing explanation of routing and parsing responsibilities. |
| `DEV.md` | developer map | Internal orientation for maintainers. |
| `document_parser_protocol.py` | `DocumentParserProtocol` | Structural contract for parser-like objects. |

### `orchestration/`

| File | Main classes | Why it exists |
| --- | --- | --- |
| `orchestration/document_parser.py` | `DocumentParser` | Central parser orchestration entrypoint. |
| `orchestration/loaded_document_parser_pipeline.py` | `LoadedDocumentParserPipeline` | Adapts `FileLoadResult` into terminal parser-stage results. |
| `orchestration/parser_selection_strategy.py` | `ParserSelectionStrategy` | Deterministic route planner for backend order. |
| `orchestration/parser_backend_registry.py` | `ParserBackendRegistry` | Lazily builds and returns backend instances by name. |
| `orchestration/parser_chain_executor.py` | `ParserChainExecutor` | Executes the selected parser order and records attempts. |
| `orchestration/parser_provenance_annotator.py` | `ParserProvenanceAnnotator` | Adds provenance and confidence to final blocks. |
| `orchestration/parse_confidence_scorer.py` | `ParseConfidenceScorer` | Produces parse-confidence signals used in block metadata. |
| `orchestration/error_classification.py` | error helpers | Maps parse failures into stable reason codes for attempt records. |
| `orchestration/manual_recovery_required_error.py` | `ManualRecoveryRequiredError` | Distinguishes quarantine from generic parser failure. |
| `orchestration/__init__.py` | exports | Keeps orchestration imports stable. |

### `backends/`

| File | Main classes | Why it exists |
| --- | --- | --- |
| `backends/base_document_parser.py` | `BaseDocumentParser` | Shared abstract base for parser backends. |
| `backends/docling_backend.py` | `DoclingParser` | Primary structured parser for native PDFs and rich layout extraction. |
| `backends/ocr_only_backend.py` | `OCROnlyParser` | OCR-first parser for scanned/image-heavy documents. |
| `backends/pymupdf_parser.py` | `PyMuPDFParser` | Lightweight parser/fallback path, especially useful outside Docling. |
| `backends/unstructured_parser.py` | `UnstructuredParser` | Secondary parser path for non-primary formats and fallback. |
| `backends/manual_recovery_parser.py` | `ManualRecoveryParser` | Explicit end-of-chain parser that signals automation exhaustion. |
| `backends/html_text_extractor.py` | `HtmlTextExtractor` | HTML text extraction helper used by lightweight parser paths. |
| `backends/__init__.py` | exports | Namespace convenience. |

### `docling/`

| File | Main classes | Why it exists |
| --- | --- | --- |
| `docling/converter_factory.py` | `DoclingConverterFactory` | Builds Docling converters from config/runtime settings. |
| `docling/pipeline_options_factory.py` | `DoclingPipelineOptionsFactory` | Produces Docling pipeline options from parser config. |
| `docling/result_normalizer.py` | `DoclingResultNormalizer` | Converts Docling output into canonical parser payloads. |
| `docling/runtime.py` | `DoclingRuntime` | Warmup/runtime validation for Docling dependencies and artifacts. |
| `docling/__init__.py` | exports | Namespace convenience. |

### `ocr/`

| File | Main classes | Why it exists |
| --- | --- | --- |
| `ocr/ocr_extractor.py` | `OCRExtractor` | Abstract OCR extraction contract. |
| `ocr/tesseract_ocr_extractor.py` | `TesseractOCRExtractor` | Concrete Tesseract-based OCR text extraction. |
| `ocr/pdf_page_rasterizer.py` | `PdfPageRasterizer` | Converts PDF pages into images before OCR. |
| `ocr/ocr_runtime.py` | `OcrRuntimeValidator` | Validates OCR runtime availability/config at startup. |
| `ocr/__init__.py` | exports | Namespace convenience. |

### `builders/`

| File | Main classes | Why it exists |
| --- | --- | --- |
| `builders/parsed_block_factory.py` | `ParsedBlockFactory` | Normalizes backend output into canonical `ParsedBlock` objects. |
| `builders/parsed_block_builder.py` | `ParsedBlockBuilder` | Shared helper for constructing canonical parsed blocks safely. |
| `builders/__init__.py` | exports | Namespace convenience. |

### `schemas/`

| File | Main models/enums | Why it exists |
| --- | --- | --- |
| `schemas/parser_config.py` | `ParserConfig` | Master parser configuration object. |
| `schemas/parser_pdf_routing_config.py` | `ParserPdfRoutingConfig` | Heuristic thresholds for scanned/image-heavy PDF routing. |
| `schemas/parser_ocr_config.py` | `ParserOcrConfig` | OCR runtime/config knobs. |
| `schemas/parser_ocr_engine.py` | `ParserOcrEngine` | OCR engine enum for parser settings. |
| `schemas/parser_backend.py` | `ParserBackend` | Backend-name enum for routing and reporting. |
| `schemas/parser_selection.py` | `ParserSelection` | Deterministic parser route plan. |
| `schemas/parse_attempt.py` | `ParseAttempt` | One backend attempt in the chain. |
| `schemas/document_parse_result.py` | `DocumentParseResult` | Full parse result and audit report for one document. |
| `schemas/loaded_document_parse_result.py` | `LoadedDocumentParseResult` | Terminal wrapper result used by the parser pipeline. |
| `schemas/loaded_document_parse_status.py` | `LoadedDocumentParseStatus` | `parsed` / `rejected` / `failed` / `quarantined` enum. |
| `schemas/parsed_block.py` | `ParsedBlock` | Canonical downstream block model. |
| `schemas/parsed_page.py` | `ParsedPage` | Page-level grouping structure. |
| `schemas/ocr_text_block.py` | `OCRTextBlock` | OCR extraction payload. |
| `schemas/rasterized_page.py` | `RasterizedPage` | Rasterized PDF page DTO for OCR. |
| `schemas/docling_config.py` | `DoclingConfig` | Docling-specific parser settings. |
| `schemas/docling_ocr_config.py` | `DoclingOcrConfig` | OCR config used within Docling mode. |
| `schemas/docling_ocr_engine.py` | `DoclingOcrEngine` | Docling OCR engine enum. |
| `schemas/docling_accelerator_config.py` | `DoclingAcceleratorConfig` | Accelerator/runtime config for Docling. |
| `schemas/docling_accelerator_device.py` | `DoclingAcceleratorDevice` | Docling accelerator device enum. |
| `schemas/docling_table_mode.py` | `DoclingTableMode` | Table extraction mode enum. |
| `schemas/__init__.py` | exports | Public schema export surface. |

## Class Ownership Guide

This section is the fastest way to answer "where should I change this?"

| Class | Owns | Does not own |
| --- | --- | --- |
| `DocumentParser` | parser orchestration and final result construction | path safety, upload validation |
| `LoadedDocumentParserPipeline` | stable terminal statuses for parsed/rejected/failed/quarantined flows | backend-specific parsing |
| `ParserSelectionStrategy` | backend order and route reason | actually running parsers |
| `ParserBackendRegistry` | backend object creation/retrieval | route selection |
| `ParserChainExecutor` | attempt execution, fallback progression, first-success semantics | deciding route policy |
| `ParsedBlockFactory` | normalizing backend payloads into canonical blocks | provenance scoring policy |
| `ParserProvenanceAnnotator` | metadata and confidence attachment | backend parsing itself |
| `ParseConfidenceScorer` | confidence scoring heuristics | parser selection |
| `DoclingParser` | Docling-based parsing path | generic fallback orchestration |
| `PyMuPDFParser` | lightweight extraction/fallback parsing | parser chain coordination |
| `UnstructuredParser` | secondary extraction path | route policy |
| `OCROnlyParser` | OCR-first parsing for scanned/image-heavy docs | general PDF strategy |
| `ManualRecoveryParser` | explicit automation stop/quarantine route | real extraction |
| `DoclingRuntime` | Docling preload/runtime validation | parsing output normalization |
| `DoclingResultNormalizer` | shaping Docling output into parser data | backend selection |
| `PdfPageRasterizer` | page-to-image conversion for OCR | OCR text parsing itself |
| `TesseractOCRExtractor` | OCR text extraction | parser-chain orchestration |
| `OcrRuntimeValidator` | runtime readiness checks for OCR tooling | routing decisions |
| `HtmlTextExtractor` | HTML text extraction helper | file safety or routing policy |

## Naming Notes

- top-level modules act as package entrypoints for parser-facing imports
- `parse_document()` in `__init__.py` is a legacy convenience function that
  returns a dictionary-based payload instead of canonical parser models

## Common Developer Tasks

### "The wrong parser backend is being chosen"

Check in this order:

1. upstream `file_ingestion` detection output
2. `orchestration/parser_selection_strategy.py`
3. `schemas/parser_selection.py`

Usually the bug is in route selection signals, not in the backend itself.

### "Fallback is not happening the way I expected"

Start here:

- `orchestration/parser_chain_executor.py`
- `orchestration/parser_backend_registry.py`
- `orchestration/error_classification.py`

Important rule: the first non-empty backend result wins. Later parsers do not
get a chance to "improve" a successful earlier parse.

### "A document should be quarantined, not just marked failed"

Start here:

- `backends/manual_recovery_parser.py`
- `orchestration/manual_recovery_required_error.py`
- `orchestration/loaded_document_parser_pipeline.py`

Manual recovery is a distinct path, not a generic exception. The pipeline
maps it to `quarantined`.

### "OCR behavior seems broken"

Start here:

- `backends/ocr_only_backend.py`
- `ocr/ocr_runtime.py`
- `ocr/pdf_page_rasterizer.py`
- `ocr/tesseract_ocr_extractor.py`
- `schemas/parser_ocr_config.py`

Also inspect route selection for `scanned_pdf` and `image_heavy` signals.

### "Docling startup or warmup is slow/failing"

Start here:

- `backends/docling_backend.py`
- `docling/runtime.py`
- `docling/converter_factory.py`
- `docling/pipeline_options_factory.py`
- `schemas/docling_config.py`

`DocumentParser.preload()` intentionally warms Docling and OCR because cold
start cost is user-visible in services.

### "Parsed blocks look inconsistent across backends"

Start here:

- `builders/parsed_block_factory.py`
- `builders/parsed_block_builder.py`
- `orchestration/parser_provenance_annotator.py`
- backend normalizers such as `docling/result_normalizer.py`

Canonical output consistency should be fixed at normalization/build/provenance
layers instead of pushing backend-specific quirks downstream.

### "Confidence or provenance metadata looks wrong"

Start here:

- `orchestration/parser_provenance_annotator.py`
- `orchestration/parse_confidence_scorer.py`
- `schemas/parsed_block.py`
- `schemas/document_parse_result.py`

## Result Objects and How They Relate

### `ParserSelection`

The route plan.
Contains:

- primary parser name
- parser order
- fallback chain
- route reason
- OCR/scanned/image-heavy/encrypted flags

### `ParseAttempt`

One backend attempt.
Contains:

- parser name
- success/failure
- fallback step
- block count
- failure reason and error metadata when relevant

### `DocumentParseResult`

Full parser report for one document.
Contains:

- final blocks
- all attempts
- winning parser
- fallback used
- OCR/scanned/image-heavy flags
- manual recovery flag

### `LoadedDocumentParseResult`

Adapter result used by `LoadedDocumentParserPipeline`.
Adds a terminal status around:

- a successful `DocumentParseResult`
- or a stable rejected/failed/quarantined outcome

## Debugging Checklist

When parsing behavior is confusing, trace it in this order:

1. `FileLoadResult` from file ingestion
2. `DocumentParser.parse_loaded_file()`
3. `ParserSelectionStrategy.select()`
4. `ParserBackendRegistry.get()`
5. `ParserChainExecutor.execute()`
6. `ParsedBlockFactory.build_blocks()`
7. `ParserProvenanceAnnotator.annotate()`
8. final `DocumentParseResult` or `LoadedDocumentParseResult`

Ask these questions:

1. Was the file actually parser-ready upstream?
2. Which route reason was chosen?
3. Which backend failed first, and how was that classified?
4. Did a backend return empty output rather than throwing?
5. Did OCR get chosen because of scanned/image-heavy heuristics?
6. Was manual recovery triggered intentionally or by accident?
7. Are final block metadata fields consistent with the winning backend?

## Editing Guidelines

- Keep routing policy in `ParserSelectionStrategy`, not spread across
  individual backends.
- Keep backend creation in `ParserBackendRegistry`, not in call sites.
- Keep canonical output shaping in factories/builders/annotators, not mixed
  into every backend.
- Preserve `ParseAttempt` detail because this package depends on auditability.
- Be careful with compatibility shims in top-level imports and aliases.
- If you add a new backend, wire all of these:
  `schemas/parser_backend.py`, registry, selection strategy, executor tests,
  and any provenance/confidence assumptions.

## Good Places To Read First

If you are new to this package, read these in order:

1. `README.md`
2. `orchestration/loaded_document_parser_pipeline.py`
3. `orchestration/document_parser.py`
4. `orchestration/parser_selection_strategy.py`
5. `orchestration/parser_chain_executor.py`
6. `builders/parsed_block_factory.py`
7. `orchestration/parser_provenance_annotator.py`
8. `schemas/document_parse_result.py`

That sequence gives you the shortest path from "approved file" to
"canonical parsed blocks with full provenance".
