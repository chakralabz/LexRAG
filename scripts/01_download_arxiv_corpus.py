"""Downloads an arXiv CS/ML corpus (PDF + metadata) for retrieval evaluation."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path

from tqdm import tqdm

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lexrag.utils.cli import add_optional_limit_args, resolve_optional_limit
from lexrag.utils.logging import get_logger

ARXIV_API = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ArxivRecord:
    """Normalized metadata record for one arXiv paper."""

    arxiv_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    published: str
    pdf_url: str


def parse_args() -> argparse.Namespace:
    """Parses CLI arguments for arXiv corpus download."""
    parser = argparse.ArgumentParser(description="Download arXiv CS/ML corpus")
    parser.add_argument(
        "--categories",
        nargs="+",
        default=["cs.LG", "cs.AI", "cs.CL"],
        help="arXiv categories (e.g. cs.LG cs.AI)",
    )
    add_optional_limit_args(
        parser,
        arg_name="max-results",
        default=50,
        help_text="Maximum papers to fetch.",
        no_limit_help_text="Fetch all available papers for the query.",
    )
    parser.add_argument("--batch-size", type=int, default=25, help="API page size")
    parser.add_argument(
        "--output-dir",
        default="data/arxiv/raw",
        help="Output root containing pdf/ and metadata/",
    )
    parser.add_argument(
        "--sort-by",
        choices=["submittedDate", "lastUpdatedDate", "relevance"],
        default="submittedDate",
    )
    parser.add_argument(
        "--sort-order",
        choices=["ascending", "descending"],
        default="descending",
    )
    parser.add_argument("--sleep-seconds", type=float, default=1.5)
    parser.add_argument(
        "--user-agent",
        default="LexRAG/1.0 (contact: opensource@example.com)",
        help="User-Agent header for arXiv API/PDF requests",
    )
    parser.add_argument("--max-retries", type=int, default=5)
    return parser.parse_args()


def _build_search_query(categories: list[str]) -> str:
    return " OR ".join(f"cat:{cat}" for cat in categories)


def _request_feed(
    *,
    query: str,
    start: int,
    max_results: int,
    sort_by: str,
    sort_order: str,
    user_agent: str,
    max_retries: int,
) -> bytes:
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": start,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
    )
    req = urllib.request.Request(
        f"{ARXIV_API}?{params}", headers={"User-Agent": user_agent}
    )
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code != HTTPStatus.TOO_MANY_REQUESTS or attempt == max_retries - 1:
                raise
            delay = 2**attempt
            logger.warning(
                "arXiv API 429, retrying in %ds (attempt %d)", delay, attempt + 1
            )
            time.sleep(delay)
    raise RuntimeError("Exceeded max retries for arXiv API")


def _entry_id(raw_id: str) -> str:
    return raw_id.rstrip("/").split("/")[-1]


def _entry_pdf_url(entry: ET.Element, arxiv_id: str) -> str:
    for link in entry.findall("atom:link", ATOM_NS):
        if link.attrib.get("title") == "pdf":
            href = link.attrib.get("href")
            if href:
                return href
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


def _parse_feed(payload: bytes) -> list[ArxivRecord]:
    root = ET.fromstring(payload)
    records: list[ArxivRecord] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        raw_id = entry.findtext("atom:id", default="", namespaces=ATOM_NS).strip()
        if not raw_id:
            continue
        records.append(_parse_entry(entry, raw_id=raw_id))
    return records


def _parse_entry(entry: ET.Element, *, raw_id: str) -> ArxivRecord:
    arxiv_id = _entry_id(raw_id)
    title = entry.findtext("atom:title", default="", namespaces=ATOM_NS).strip()
    summary = entry.findtext("atom:summary", default="", namespaces=ATOM_NS).strip()
    published = entry.findtext("atom:published", default="", namespaces=ATOM_NS).strip()
    authors = [
        author.findtext("atom:name", default="", namespaces=ATOM_NS).strip()
        for author in entry.findall("atom:author", ATOM_NS)
    ]
    categories = [
        category.attrib.get("term", "").strip()
        for category in entry.findall("atom:category", ATOM_NS)
        if category.attrib.get("term")
    ]
    return ArxivRecord(
        arxiv_id=arxiv_id,
        title=title,
        summary=summary,
        authors=[author for author in authors if author],
        categories=categories,
        published=published,
        pdf_url=_entry_pdf_url(entry, arxiv_id),
    )


def _download_file(
    url: str, out_path: Path, *, user_agent: str, max_retries: int
) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                payload = response.read()
            out_path.write_bytes(payload)
            return len(payload)
        except urllib.error.HTTPError as exc:
            if exc.code != HTTPStatus.TOO_MANY_REQUESTS or attempt == max_retries - 1:
                raise
            delay = 2**attempt
            logger.warning(
                "arXiv PDF 429, retrying in %ds (attempt %d)", delay, attempt + 1
            )
            time.sleep(delay)
    raise RuntimeError("Exceeded max retries for arXiv PDF")


def _prepare_output_dirs(output_dir: str) -> tuple[Path, Path, Path]:
    output_root = Path(output_dir)
    pdf_dir = output_root / "pdf"
    metadata_dir = output_root / "metadata"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    return output_root, pdf_dir, metadata_dir


def _fetch_records(
    args: argparse.Namespace, *, max_results: int | None
) -> list[ArxivRecord]:
    query = _build_search_query(args.categories)
    fetched: list[ArxivRecord] = []
    seen_ids: set[str] = set()
    start = 0
    with tqdm(
        total=max_results, desc="Fetching arXiv metadata", unit="paper"
    ) as fetch_progress:
        while True:
            should_stop, batch_size = _resolve_batch_size(
                start=start, args=args, max_results=max_results
            )
            if should_stop:
                break
            records = _fetch_batch(
                args=args, query=query, start=start, batch_size=batch_size
            )
            if not records:
                break
            new_records = _append_unique_records(
                records, fetched=fetched, seen_ids=seen_ids
            )
            fetch_progress.update(new_records)
            start += batch_size
            if _should_end_pagination(
                args=args,
                max_results=max_results,
                records=records,
                new_records=new_records,
            ):
                break
    if max_results is not None and len(fetched) > max_results:
        return fetched[:max_results]
    return fetched


def _resolve_batch_size(
    *,
    start: int,
    args: argparse.Namespace,
    max_results: int | None,
) -> tuple[bool, int]:
    if max_results is not None and start >= max_results:
        return True, 0
    batch_size = args.batch_size
    if max_results is not None:
        batch_size = min(args.batch_size, max_results - start)
        if batch_size <= 0:
            return True, 0
    return False, batch_size


def _fetch_batch(
    *,
    args: argparse.Namespace,
    query: str,
    start: int,
    batch_size: int,
) -> list[ArxivRecord]:
    payload = _request_feed(
        query=query,
        start=start,
        max_results=batch_size,
        sort_by=args.sort_by,
        sort_order=args.sort_order,
        user_agent=args.user_agent,
        max_retries=args.max_retries,
    )
    records = _parse_feed(payload)
    time.sleep(max(args.sleep_seconds, 0.0))
    return records


def _append_unique_records(
    records: list[ArxivRecord],
    *,
    fetched: list[ArxivRecord],
    seen_ids: set[str],
) -> int:
    new_records = 0
    for record in records:
        if record.arxiv_id in seen_ids:
            continue
        seen_ids.add(record.arxiv_id)
        fetched.append(record)
        new_records += 1
    return new_records


def _should_end_pagination(
    *,
    args: argparse.Namespace,
    max_results: int | None,
    records: list[ArxivRecord],
    new_records: int,
) -> bool:
    if max_results is not None:
        return False
    return len(records) < args.batch_size or new_records == 0


def _download_pdfs(
    records: list[ArxivRecord],
    *,
    pdf_dir: Path,
    user_agent: str,
    max_retries: int,
) -> tuple[int, int, int, int]:
    total_bytes = 0
    downloaded = 0
    skipped = 0
    failures = 0
    for record in tqdm(records, desc="Downloading PDFs", unit="pdf"):
        file_name = f"{record.arxiv_id.replace('/', '_')}.pdf"
        out_path = pdf_dir / file_name
        if out_path.exists() and out_path.stat().st_size > 1024:
            skipped += 1
            continue
        try:
            size = _download_file(
                record.pdf_url,
                out_path,
                user_agent=user_agent,
                max_retries=max_retries,
            )
            total_bytes += size
            downloaded += 1
        except urllib.error.URLError:
            failures += 1
    return total_bytes, downloaded, skipped, failures


def _write_metadata(
    records: list[ArxivRecord], *, pdf_dir: Path, metadata_dir: Path
) -> Path:
    metadata_path = metadata_dir / "papers.jsonl"
    with metadata_path.open("w", encoding="utf-8") as handle:
        for record in records:
            payload = {
                "arxiv_id": record.arxiv_id,
                "title": record.title,
                "summary": record.summary,
                "authors": record.authors,
                "categories": record.categories,
                "published": record.published,
                "pdf_url": record.pdf_url,
                "pdf_path": str(
                    (pdf_dir / f"{record.arxiv_id.replace('/', '_')}.pdf").resolve()
                ),
            }
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    return metadata_path


def _log_summary(
    *,
    fetched_count: int,
    summary: tuple[int, int, int, int],
    metadata_path: Path,
) -> None:
    total_bytes, downloaded, skipped, failures = summary
    mb = total_bytes / (1024 * 1024)
    logger.info(
        "arXiv download complete: records=%d downloaded=%d skipped=%d failed=%d total_mb=%.2f metadata=%s",
        fetched_count,
        downloaded,
        skipped,
        failures,
        mb,
        metadata_path,
    )


def main() -> int:
    """Downloads arXiv metadata and PDFs into local data directory."""
    args = parse_args()
    max_results = resolve_optional_limit(
        args,
        limit_dest="max_results",
        no_limit_dest="no_max_results_limit",
    )
    _, pdf_dir, metadata_dir = _prepare_output_dirs(args.output_dir)
    records = _fetch_records(args, max_results=max_results)
    summary = _download_pdfs(
        records,
        pdf_dir=pdf_dir,
        user_agent=args.user_agent,
        max_retries=args.max_retries,
    )
    metadata_path = _write_metadata(records, pdf_dir=pdf_dir, metadata_dir=metadata_dir)
    _log_summary(
        fetched_count=len(records), summary=summary, metadata_path=metadata_path
    )
    return 0 if summary[3] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
