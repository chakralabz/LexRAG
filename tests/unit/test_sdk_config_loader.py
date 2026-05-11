from __future__ import annotations

from pathlib import Path

from lexrag.config import ConfigLoader


def test_config_loader_applies_yaml_env_and_overrides(
    monkeypatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "lexrag.yaml"
    config_path.write_text(
        "\n".join(
            [
                "logging:",
                "  level: WARNING",
                "models:",
                "  embed_model: yaml-model",
                "ingestion:",
                "  embed_batch_size: 8",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("EMBED_MODEL", "env-model")
    monkeypatch.setenv("LEXRAG_LOG_LEVEL", "ERROR")

    settings = ConfigLoader().load(
        config_path=config_path,
        overrides={"embed_batch_size": 16},
    )

    assert settings.log_level == "ERROR"
    assert settings.embed_model == "env-model"
    assert settings.embed_batch_size == 16
    assert settings.config_path == config_path
