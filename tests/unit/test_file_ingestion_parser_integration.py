from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from lexrag.ingestion.parser import FallbackDocumentParser, ParsedBlock


def test_parser_rejects_invalid_file_before_parser_execution(tmp_path: Path) -> None:
    blocked = tmp_path / "payload.exe"
    blocked.write_bytes(b"MZfake")
    parser = FallbackDocumentParser(
        primary_parser=SimpleNamespace(parse=lambda path: []),
        fallback_parser=SimpleNamespace(parse=lambda path: []),
    )

    with pytest.raises(ValueError, match="unsupported_extension"):
        parser.parse_document(blocked)


def test_parser_uses_file_ingestion_gateway_before_selection(tmp_path: Path) -> None:
    html_path = tmp_path / "sample.html"
    html_path.write_text("<html><body>hello</body></html>", encoding="utf-8")
    parser = FallbackDocumentParser(
        primary_parser=SimpleNamespace(parse=lambda path: []),
        fallback_parser=SimpleNamespace(
            parse=lambda path: [
                ParsedBlock(
                    block_id="blk_1",
                    page=1,
                    section="HTML",
                    text=f"parsed:{path.name}",
                )
            ]
        ),
    )

    parsed = parser.parse_document(html_path)

    assert parsed[0].text == "parsed:sample.html"


def test_parser_accepts_image_documents_for_ocr_routes(tmp_path: Path) -> None:
    image_path = tmp_path / "scan.png"
    image_path.write_bytes(b"fake-image")
    parser = FallbackDocumentParser(
        ocr_parser=SimpleNamespace(
            parse=lambda path: [
                ParsedBlock(
                    block_id="blk_ocr_1",
                    page=1,
                    section="OCR Page 1",
                    text=f"ocr:{path.name}",
                    is_ocr=True,
                    ocr_used="stub_ocr",
                )
            ]
        ),
        primary_parser=SimpleNamespace(parse=lambda path: []),
        fallback_parser=SimpleNamespace(parse=lambda path: []),
    )

    parsed = parser.parse_document(image_path)

    assert parsed[0].text == "ocr:scan.png"
    assert parsed[0].is_ocr is True
