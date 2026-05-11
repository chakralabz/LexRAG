from __future__ import annotations

from lexrag.config import Settings
from lexrag.generation.llm_backend import LLMBackend
from lexrag.serving.server import main


class FakeBackend(LLMBackend):
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        _ = system_prompt, user_prompt, max_tokens, temperature
        return "ok"


def test_server_main_wires_host_and_port(monkeypatch) -> None:
    captured: dict[str, object] = {}
    sentinel_app = object()

    def fake_create_app(**kwargs) -> object:
        _ = kwargs
        return sentinel_app

    def fake_settings() -> Settings:
        return Settings(
            LEXRAG_ENV="TEST",
            API_SECRET_KEY="secret",
            LEXRAG_USE_REAL_STORES=True,
        )

    def fake_run_server(**kwargs) -> int:
        captured.update(kwargs)
        return 7

    monkeypatch.setattr(
        "lexrag.serving.server.create_app",
        fake_create_app,
    )
    monkeypatch.setattr("lexrag.serving.server.get_settings", fake_settings)
    monkeypatch.setattr("lexrag.serving.server.run_server", fake_run_server)

    result = main(
        ["--host", "127.0.0.1", "--port", "8123"],
        llm_backend=FakeBackend(),
    )

    assert result == 7
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8123
    assert captured["app"] is sentinel_app
