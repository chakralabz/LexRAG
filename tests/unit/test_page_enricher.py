from __future__ import annotations

from pathlib import Path

from lexrag.ingestion.page_enricher import (
    HeuristicDocumentTypeResolver,
    PagePayloadEnricher,
    StaticDocumentTypeResolver,
)


def test_page_payload_enricher_heuristic_doc_type_resolution() -> None:
    enricher = PagePayloadEnricher(resolver=HeuristicDocumentTypeResolver())
    pages = [{"text": "sample text", "section": "HTML"}]
    path = Path("data/sec/sample_10-k.html")
    enriched = enricher.enrich(pages, path=path)

    assert len(enriched) == 1
    assert enriched[0]["doc_type"] == "sec_filing"
    assert enriched[0]["section"] == "Document"
    assert enriched[0]["doc_id"] == "sample_10-k"


def test_page_payload_enricher_static_doc_type_resolution() -> None:
    enricher = PagePayloadEnricher(
        resolver=StaticDocumentTypeResolver(doc_type="research_paper")
    )
    pages = [{"text": "paper content"}]
    path = Path("data/arxiv/raw/pdf/paper_01.pdf")
    enriched = enricher.enrich(pages, path=path)

    assert len(enriched) == 1
    assert enriched[0]["doc_type"] == "research_paper"
    assert enriched[0]["source_path"] == str(path)
    assert enriched[0]["page"] == 1
