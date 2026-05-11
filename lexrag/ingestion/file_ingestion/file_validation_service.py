"""File validation service for architecture layer 2.1.

This service owns pre-parse safety checks only. It intentionally stops short of
parser concerns so callers can reject risky uploads with deterministic, user-
facing validation issues before any expensive parser dependency is invoked.
"""

from __future__ import annotations

from pathlib import Path

from lexrag.ingestion.file_ingestion.antivirus.antivirus_scanner import (
    AntivirusScanner,
)
from lexrag.ingestion.file_ingestion.antivirus.build_antivirus_scanner import (
    build_antivirus_scanner,
)
from lexrag.ingestion.file_ingestion.classification.extension_media_type_policy import (
    ExtensionMediaTypePolicy,
)
from lexrag.ingestion.file_ingestion.file_hash_calculator import FileHashCalculator
from lexrag.ingestion.file_ingestion.magic_bytes_sniffer import MagicBytesSniffer
from lexrag.ingestion.file_ingestion.schemas.antivirus_scan_result import (
    AntivirusScanResult,
)
from lexrag.ingestion.file_ingestion.schemas.file_ingestion_config import (
    FileIngestionConfig,
)
from lexrag.ingestion.file_ingestion.schemas.file_validation_issue import (
    FileValidationIssue,
)
from lexrag.ingestion.file_ingestion.schemas.file_validation_result import (
    FileValidationResult,
)
from lexrag.ingestion.file_ingestion.validation.file_integrity_inspector import (
    FileIntegrityInspector,
)
from lexrag.ingestion.file_ingestion.validation.validation_issue_factory import (
    ValidationIssueFactory,
)


class FileValidationService:
    """Validate file safety, integrity, and batch-level uniqueness."""

    def __init__(
        self,
        config: FileIngestionConfig | None = None,
        *,
        antivirus_scanner: AntivirusScanner | None = None,
        hash_calculator: FileHashCalculator | None = None,
        sniffer: MagicBytesSniffer | None = None,
    ) -> None:
        """Initialize validation collaborators.

        Args:
            config: Optional ingestion configuration.
            antivirus_scanner: Optional malware scanner implementation.
            hash_calculator: Optional file hash implementation.
            sniffer: Optional byte-level content sniffer.
        """
        self.config = config or FileIngestionConfig()
        self.antivirus_scanner = antivirus_scanner or build_antivirus_scanner(
            config=self.config
        )
        self.hash_calculator = hash_calculator or FileHashCalculator()
        self.sniffer = sniffer or MagicBytesSniffer(config=self.config)
        self.media_type_policy = ExtensionMediaTypePolicy(config=self.config)
        self.integrity_inspector = FileIntegrityInspector(config=self.config)
        self.issue_factory = ValidationIssueFactory(config=self.config)

    def validate(
        self,
        path: Path,
        *,
        known_hashes: set[str] | None = None,
    ) -> FileValidationResult:
        """Validate a single file before parser selection begins.

        Args:
            path: File path to validate.
            known_hashes: Optional in-memory batch hash set for duplicate checks.

        Returns:
            Structured validation result with blocking and non-blocking issues.
        """
        self._assert_path(path)
        media_type, _method = self.sniffer.sniff(path)
        sha256 = self.hash_calculator.sha256(path)
        issues = self._build_issues(path=path, media_type=media_type, sha256=sha256)
        duplicate_in_batch = self._track_batch_duplicate(
            sha256=sha256,
            known_hashes=known_hashes,
        )
        if duplicate_in_batch:
            issues.append(
                self._build_issue("duplicate_file_in_batch", blocking=True)
            )
        antivirus = self.antivirus_scanner.scan(path)
        if antivirus.blocking:
            issues.append(self._build_issue("antivirus_infected", blocking=True))
        return self._build_result(
            path=path,
            media_type=media_type,
            sha256=sha256,
            antivirus=antivirus,
            duplicate_in_batch=duplicate_in_batch,
            issues=issues,
        )

    def validate_many(self, paths: list[Path]) -> list[FileValidationResult]:
        """Validate a batch and detect duplicate uploads within that batch.

        Args:
            paths: File paths to validate together.

        Returns:
            Validation results in the same order as the input paths.
        """
        known_hashes: set[str] = set()
        return [self.validate(path, known_hashes=known_hashes) for path in paths]

    def _build_issues(
        self,
        *,
        path: Path,
        media_type: str,
        sha256: str,
    ) -> list[FileValidationIssue]:
        """Collect deterministic validation issues for a file.

        Args:
            path: File path to validate.
            media_type: Detected MIME-like media type.
            sha256: SHA-256 digest for the file.

        Returns:
            Structured validation issues for the file.
        """
        issues: list[FileValidationIssue] = []
        self._append_size_issues(path=path, issues=issues)
        self._append_extension_issues(path=path, media_type=media_type, issues=issues)
        self._append_corruption_issue(path=path, media_type=media_type, issues=issues)
        self._append_encryption_issue(path=path, media_type=media_type, issues=issues)
        self._append_page_count_issue(path=path, media_type=media_type, issues=issues)
        self._append_hash_presence_issue(sha256=sha256, issues=issues)
        return issues

    def _append_size_issues(
        self,
        *,
        path: Path,
        issues: list[FileValidationIssue],
    ) -> None:
        """Enforce minimum and maximum document size thresholds.

        Args:
            path: File path to validate.
            issues: Mutable issue list to append to.
        """
        size_bytes = path.stat().st_size
        if size_bytes < self.config.min_file_size_bytes:
            issues.append(self._build_issue("file_empty", blocking=True))
        if size_bytes > self.config.max_file_size_bytes:
            issues.append(self._build_issue("file_too_large", blocking=True))

    def _append_extension_issues(
        self,
        *,
        path: Path,
        media_type: str,
        issues: list[FileValidationIssue],
    ) -> None:
        """Validate allowlisted extensions and content-type consistency.

        Args:
            path: File path to validate.
            media_type: Detected MIME-like media type.
            issues: Mutable issue list to append to.
        """
        extension = path.suffix.lower()
        if not self.media_type_policy.is_allowed_extension(extension):
            issues.append(self._build_issue("unsupported_extension", blocking=True))
            return
        if self.media_type_policy.matches(extension=extension, media_type=media_type):
            return
        issues.append(self._build_issue("extension_media_mismatch", blocking=False))

    def _append_corruption_issue(
        self,
        *,
        path: Path,
        media_type: str,
        issues: list[FileValidationIssue],
    ) -> None:
        """Block obviously malformed PDFs and OOXML archives early.

        Args:
            path: File path to validate.
            media_type: Detected MIME-like media type.
            issues: Mutable issue list to append to.
        """
        if self.integrity_inspector.is_corrupted(path=path, media_type=media_type):
            issues.append(self._build_issue("corrupt_file", blocking=True))

    def _append_encryption_issue(
        self,
        *,
        path: Path,
        media_type: str,
        issues: list[FileValidationIssue],
    ) -> None:
        """Detect password-protected PDFs before parser execution.

        Args:
            path: File path to validate.
            media_type: Detected MIME-like media type.
            issues: Mutable issue list to append to.
        """
        if not self.integrity_inspector.is_encrypted_pdf(
            path=path,
            media_type=media_type,
        ):
            return
        issues.append(self._build_issue("encrypted_pdf", blocking=True))

    def _append_page_count_issue(
        self,
        *,
        path: Path,
        media_type: str,
        issues: list[FileValidationIssue],
    ) -> None:
        """Block paged files that exceed the configured page count limit.

        Args:
            path: File path to validate.
            media_type: Detected MIME-like media type.
            issues: Mutable issue list to append to.
        """
        max_page_count = self.config.max_page_count
        if max_page_count is None:
            return
        page_count = self._page_count(path=path, media_type=media_type)
        if page_count is None:
            return
        if page_count > max_page_count:
            issues.append(self._build_issue("file_too_many_pages", blocking=True))

    def _append_hash_presence_issue(
        self,
        *,
        sha256: str,
        issues: list[FileValidationIssue],
    ) -> None:
        """Guard against impossible hashing failures and empty digests.

        Args:
            sha256: SHA-256 digest for the file.
            issues: Mutable issue list to append to.
        """
        if sha256:
            return
        issues.append(self._build_issue("hash_unavailable", blocking=True))

    def _build_result(
        self,
        *,
        path: Path,
        media_type: str,
        sha256: str,
        antivirus: AntivirusScanResult,
        duplicate_in_batch: bool,
        issues: list[FileValidationIssue],
    ) -> FileValidationResult:
        """Materialize the canonical validation DTO.

        Args:
            path: File path that was validated.
            media_type: Detected MIME-like media type.
            sha256: SHA-256 digest for the file.
            antivirus: Antivirus scan result for the file.
            duplicate_in_batch: Whether the file duplicated a prior batch entry.
            issues: Structured validation issues for the file.

        Returns:
            Canonical validation result for the file.
        """
        extension = path.suffix.lower()
        blocking_issues = [issue for issue in issues if issue.blocking]
        page_count = self._page_count(path=path, media_type=media_type)
        return FileValidationResult(
            path=str(path),
            extension=extension,
            file_size_bytes=path.stat().st_size,
            page_count=page_count,
            media_type=media_type,
            sha256=sha256,
            encrypted=self._has_issue("encrypted_pdf", issues=issues),
            corrupted=self._has_issue("corrupt_file", issues=issues),
            supported_extension=self.media_type_policy.is_allowed_extension(extension),
            extension_matches_media_type=self.media_type_policy.matches(
                extension=extension,
                media_type=media_type,
            ),
            duplicate_in_batch=duplicate_in_batch,
            antivirus=antivirus,
            issues=issues,
            is_valid=not blocking_issues,
            failure_reason=blocking_issues[0].code if blocking_issues else None,
        )

    def _track_batch_duplicate(
        self,
        *,
        sha256: str,
        known_hashes: set[str] | None,
    ) -> bool:
        """Track duplicate files within a single batch validation call.

        Args:
            sha256: SHA-256 digest for the current file.
            known_hashes: Mutable set shared across batch validation.

        Returns:
            True when the file digest has already been seen in the batch.
        """
        if known_hashes is None:
            return False
        already_seen = sha256 in known_hashes
        # The set is updated even for duplicates so later files keep seeing the
        # full batch history instead of a partial view.
        known_hashes.add(sha256)
        return already_seen

    def _assert_path(self, path: Path) -> None:
        """Validate basic path preconditions before deeper inspection.

        Args:
            path: File path to validate.
        """
        if not path.exists():
            raise FileNotFoundError(f"Document does not exist: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"Document is not a file: {path}")

    def _build_issue(self, code: str, *, blocking: bool) -> FileValidationIssue:
        """Create a stable issue object for a validation failure or warning.

        Args:
            code: Stable validation issue code.
            blocking: Whether the issue should block ingestion.

        Returns:
            Structured validation issue.
        """
        return self.issue_factory.build(code, blocking=blocking)

    def _page_count(self, *, path: Path, media_type: str) -> int | None:
        """Return the page count for paged formats when it can be determined.

        Args:
            path: File path to inspect.
            media_type: Detected MIME-like media type.

        Returns:
            Page count when available for the format.
        """
        if media_type != "application/pdf":
            return None
        try:
            import fitz
        except Exception:
            return None
        try:
            with fitz.open(path) as document:  # pragma: no cover
                return len(document)
        except Exception:
            return None

    def _has_issue(
        self,
        code: str,
        *,
        issues: list[FileValidationIssue],
    ) -> bool:
        """Check whether a structured issue list contains a specific code.

        Args:
            code: Validation issue code to search for.
            issues: Structured issue list to inspect.

        Returns:
            True when the issue code is present in the list.
        """
        return any(issue.code == code for issue in issues)
