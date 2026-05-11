# `lexrag.ingestion.file_ingestion` Developer Guide

This file is for developers working inside the `file_ingestion` package.
Its job is to make the package easier to navigate when you are trying to:

- understand the pre-parse ingestion boundary
- find the right place to change behavior
- debug why a file was accepted, rejected, or routed oddly

Use this guide together with
[README.md](/Users/ayushsolanki/Desktop/Projects/LexRAG/lexrag/ingestion/file_ingestion/README.md)
for the public package view.

## Why This Package Exists

This package is the trusted boundary before parsing starts.

It exists so parser code does not need to worry about:

- unsafe paths
- unsupported file types
- extension spoofing
- file corruption
- encrypted PDFs
- duplicate uploads inside a batch
- antivirus decisions

If a developer is changing parser behavior but the root cause is actually
"the file should never have been parseable in the first place", the fix
probably belongs here, not in `lexrag.ingestion.parser`.

## Mental Model

Think of this package as producing one canonical answer:

"Given this caller-supplied path, should the parser be allowed to touch it,
and if yes, what do we know about the file?"

That answer is represented by:

- `FileLoadResult`
- `FileIngestionReport`
- `FileValidationResult`
- `FileTypeDetection`

## Main Flow

```text
caller path
  -> FileLoadService
      -> FilePathResolver
      -> BatchFileCollector (directory mode only)
      -> FileInspectionService
          -> FileValidationService
              -> MagicBytesSniffer
              -> FileHashCalculator
              -> ExtensionMediaTypePolicy
              -> FileIntegrityInspector
              -> AntivirusScanner
              -> ValidationIssueFactory
          -> FileTypeDetector
              -> MagicBytesSniffer
              -> DocumentFamilyClassifier
              -> TextSampleInspector
  -> FileLoadResult
  -> parser package
```

## Entry Points You Will Usually Touch

### `file_load_service.py`

- `FileLoadService`
- Main package entrypoint for callers starting with filesystem paths
- Use this when you need to load one file or a directory tree into
  parser-ready results
- Owns path resolution, batch expansion, and failure/result packaging

### `inspection/file_inspection_service.py`

- `FileInspectionService`
- Best conceptual center of the package
- Use this when the path is already resolved and you only want validation
  plus type detection
- Combines validation and detection into one `FileIngestionReport`

### `file_validation_service.py`

- `FileValidationService`
- Owns safety/integrity checks
- If a file should be blocked, the logic usually belongs here

### `file_type_detector.py`

- `FileTypeDetector`
- Owns parser-facing document family classification
- If routing to parser backends feels wrong, inspect this first before
  changing parser selection

## Package Map

### Top-level modules

| File | Main classes/functions | Why it exists |
| --- | --- | --- |
| `__init__.py` | package exports | Keeps downstream imports stable and exposes the public API surface. |
| `README.md` | package overview | Public-facing explanation of responsibilities and usage. |
| `DEV.md` | developer map | Internal orientation for maintainers and contributors. |
| `file_load_service.py` | `FileLoadService` | Converts caller paths into structured load results. |
| `file_path_resolver.py` | `FilePathResolver` | Canonical path resolution, root checks, symlink policy, path safety. |
| `file_validation_service.py` | `FileValidationService` | Pre-parse validation logic and issue aggregation. |
| `file_type_detector.py` | `FileTypeDetector` | Byte-first classification into parser-facing document families. |
| `file_hash_calculator.py` | `FileHashCalculator` | Stable file hashing for duplicate detection and auditing. |
| `magic_bytes_sniffer.py` | `MagicBytesSniffer` | Content sniffing so extension alone is never trusted. |

### `inspection/`

| File | Main classes | Why it exists |
| --- | --- | --- |
| `inspection/file_inspection_service.py` | `FileInspectionService` | Small orchestration layer combining validation and detection. |
| `inspection/__init__.py` | exports | Keeps inspection imports simple. |

### `loading/`

| File | Main classes | Why it exists |
| --- | --- | --- |
| `loading/batch_file_collector.py` | `BatchFileCollector` | Expands directories into deterministic file lists. |
| `loading/load_failure_reason_mapper.py` | `LoadFailureReasonMapper` | Converts resolver/load exceptions into stable rejection codes. |
| `loading/__init__.py` | exports | Namespace convenience. |

### `validation/`

| File | Main classes | Why it exists |
| --- | --- | --- |
| `validation/file_integrity_inspector.py` | `FileIntegrityInspector` | Lightweight corruption and encrypted-PDF checks. |
| `validation/validation_issue_factory.py` | `ValidationIssueFactory` | Central place for structured validation issue creation. |
| `validation/__init__.py` | exports | Namespace convenience. |

### `classification/`

| File | Main classes | Why it exists |
| --- | --- | --- |
| `classification/document_family_classifier.py` | `DocumentFamilyClassifier` | Maps extension/media type pairs to parser-facing families like `pdf`, `html`, `office`, `image`. |
| `classification/extension_media_type_policy.py` | `ExtensionMediaTypePolicy` | Allowlist and extension-to-media-type policy. |
| `classification/text_sample_inspector.py` | `TextSampleInspector` | Heuristics for whether a byte sample looks text-like. |
| `classification/__init__.py` | exports | Namespace convenience. |

### `antivirus/`

| File | Main classes/functions | Why it exists |
| --- | --- | --- |
| `antivirus/antivirus_scanner.py` | `AntivirusScanner` | Abstract scanner contract. |
| `antivirus/build_antivirus_scanner.py` | `build_antivirus_scanner` | Factory that wires the configured scanner implementation. |
| `antivirus/clamav_antivirus_scanner.py` | `ClamAVAntivirusScanner` | Real ClamAV-backed scanner. |
| `antivirus/no_op_antivirus_scanner.py` | `NoOpAntivirusScanner` | Non-blocking fallback for dev/test flows without ClamAV. |
| `antivirus/__init__.py` | exports | Namespace convenience. |

### `schemas/`

| File | Main models/enums | Why it exists |
| --- | --- | --- |
| `schemas/file_ingestion_config.py` | `FileIngestionConfig` | Master config object shared across the package. |
| `schemas/file_ingestion_limits.py` | `FileIngestionLimits` | File size and page-limit settings. |
| `schemas/file_ingestion_path_config.py` | `FileIngestionPathConfig` | Allowed roots, symlink policy, and path restrictions. |
| `schemas/file_ingestion_antivirus_config.py` | `FileIngestionAntivirusConfig` | Antivirus provider and runtime settings. |
| `schemas/file_type_selection_config.py` | `FileTypeSelectionConfig` | Extension/media-type selection policy details. |
| `schemas/file_validation_issue.py` | `FileValidationIssue` | One structured validation issue. |
| `schemas/file_validation_result.py` | `FileValidationResult` | Full validation outcome for one file. |
| `schemas/file_type_detection.py` | `FileTypeDetection` | Structured detection result used by parser routing. |
| `schemas/file_ingestion_report.py` | `FileIngestionReport` | Combined validation + detection report. |
| `schemas/file_load_result.py` | `FileLoadResult` | Final load decision passed to the parser boundary. |
| `schemas/antivirus_provider.py` | `AntivirusProvider` | Antivirus provider enum. |
| `schemas/antivirus_scan_result.py` | `AntivirusScanResult` | Structured malware scan result. |
| `schemas/supported_file_type.py` | `SupportedFileType` | Public allowlist enum for accepted file types. |
| `schemas/__init__.py` | exports | Public schema export surface. |

## Class Ownership Guide

If you only remember one section from this file, make it this one.

| Class | Owns | Does not own |
| --- | --- | --- |
| `FileLoadService` | path-to-result orchestration | validation details, parser routing |
| `FilePathResolver` | filesystem safety and canonicalization | MIME detection, validation rules |
| `FileInspectionService` | orchestration of validation + detection | path expansion, parser execution |
| `FileValidationService` | safety checks and blocking decisions | parser selection |
| `FileTypeDetector` | file family detection for downstream routing | blocking/rejection policy |
| `MagicBytesSniffer` | byte-level content hints | final routing policy |
| `FileHashCalculator` | hashing | duplicate policy explanation |
| `FileIntegrityInspector` | corruption/encryption checks | parser fallback decisions |
| `ValidationIssueFactory` | issue shape and messages | deciding when a file is invalid |
| `DocumentFamilyClassifier` | mapping to high-level file families | path safety |
| `ExtensionMediaTypePolicy` | extension allowlist and match policy | malware or corruption checks |
| `BatchFileCollector` | deterministic directory expansion | per-file validation |
| `LoadFailureReasonMapper` | stable error codes for load failures | file inspection logic |
| `ClamAVAntivirusScanner` | real malware scan | validation aggregation |
| `NoOpAntivirusScanner` | dev-safe placeholder scanner | security guarantees |

## Common Developer Tasks

### "I need to allow a new file type"

Start here:

- `schemas/supported_file_type.py`
- `classification/extension_media_type_policy.py`
- `classification/document_family_classifier.py`
- `file_type_detector.py`
- `schemas/file_type_detection.py`

Usually do not start in parser code. The parser should consume the family
decision that originates here.

### "A safe file is getting rejected"

Start here:

- `file_load_service.py`
- `file_path_resolver.py`
- `file_validation_service.py`
- `validation/file_integrity_inspector.py`
- `validation/validation_issue_factory.py`

Check whether the rejection happened:

- before inspection: path problem, file/directory mismatch, permissions
- during validation: size, extension, corruption, encryption, duplicate, AV

### "The parser chose the wrong backend"

Start here:

- `file_type_detector.py`
- `classification/document_family_classifier.py`
- `magic_bytes_sniffer.py`

The parser selection layer depends heavily on the `document_family` and
media-type signals this package emits.

### "Batch ingestion order or duplicate behavior looks wrong"

Start here:

- `loading/batch_file_collector.py`
- `file_load_service.py`
- `file_validation_service.py`

Duplicate detection within a batch is driven by SHA-256 tracking in
`FileValidationService.validate_many()`.

### "Security/compliance review flagged something"

Start here:

- `file_validation_service.py`
- `antivirus/`
- `file_path_resolver.py`
- `schemas/file_ingestion_config.py`

This package is where security posture is actually enforced before parsing.

## Result Objects and How They Relate

### `FileValidationResult`

Contains:

- whether the file is valid
- blocking and non-blocking issues
- corruption/encryption flags
- page count and media type
- antivirus result

### `FileTypeDetection`

Contains:

- detected media type
- parser-facing family such as `pdf`, `html`, `office`, `image`
- whether the bytes look text-like
- whether the extension matches the content

### `FileIngestionReport`

Simple composition of:

- `validation`
- `detection`

### `FileLoadResult`

Final handoff object to the parser layer.
It contains:

- requested path
- resolved path
- the `FileIngestionReport` when inspection happened
- `is_ready`
- stable rejection reason/message for failures

## Debugging Checklist

When a file behaves strangely, trace it in this order:

1. `FileLoadService.load_file()` or `load_path()`
2. `FilePathResolver.resolve()`
3. `FileInspectionService.inspect()` or `inspect_batch()`
4. `FileValidationService.validate()` or `validate_many()`
5. `FileTypeDetector.detect()`
6. the resulting `FileLoadResult`

Ask these questions:

1. Did the path resolve into the file we expected?
2. Did validation fail before parser access?
3. Was the media type sniffed from bytes or inferred another way?
4. Did extension and media type disagree?
5. Did the document family classify into the parser family we expected?
6. Was this file marked duplicate only because of batch context?

## Editing Guidelines

- Add new policy in small helpers before growing `FileValidationService`
  or `FileTypeDetector` too much.
- If a change affects the parser route indirectly, prefer documenting the
  emitted `FileTypeDetection` fields clearly instead of hiding behavior in
  parser-side special cases.
- Keep "blocking" decisions explicit and auditable.
- Preserve stable failure/rejection codes because downstream code may rely
  on them for UI, logs, or operational metrics.
- If you add a new schema field, update both package docs and tests that
  assert the shape of results.

## Good Places To Read First

If you are new to this package, read these in order:

1. `README.md`
2. `file_load_service.py`
3. `inspection/file_inspection_service.py`
4. `file_validation_service.py`
5. `file_type_detector.py`
6. `schemas/file_load_result.py`
7. `schemas/file_ingestion_report.py`

That sequence gives you the shortest path to understanding how a raw path
turns into a parser-ready decision.
