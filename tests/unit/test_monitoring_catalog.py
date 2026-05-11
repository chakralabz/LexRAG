from __future__ import annotations

from lexrag.observability import MonitoringCatalog


def test_monitoring_catalog_contains_architecture_metrics() -> None:
    catalog = MonitoringCatalog()
    names = catalog.metric_names()

    assert "parser_success_rate" in names
    assert "vector_duplicate_rate" in names
    assert "citation_success_rate" in names


def test_monitoring_catalog_preserves_alert_thresholds() -> None:
    catalog = MonitoringCatalog()

    orphan_rate = catalog.by_name("orphan_citation_rate")
    unsupported = catalog.by_name("unsupported_answer_rate")

    assert orphan_rate.alert_threshold is not None
    assert orphan_rate.alert_threshold.warning == 0.01
    assert orphan_rate.alert_threshold.critical == 0.05
    assert unsupported.alert_threshold is not None
    assert unsupported.alert_threshold.warning == 0.10
    assert unsupported.alert_threshold.critical == 0.25
