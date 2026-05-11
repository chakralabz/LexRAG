"""Executable ASGI server for LexRAG."""

from __future__ import annotations

import argparse

from lexrag.config import Settings, get_settings
from lexrag.generation import LLMBackend
from lexrag.serving.asgi_application import LexRAGASGIApplication
from lexrag.serving.default_application import build_default_application
from lexrag.serving.fixed_window_rate_limiter import FixedWindowRateLimiter
from lexrag.serving.lexrag_application import LexRAGApplication
from lexrag.serving.request_authorizer import RequestAuthorizer


def create_app(
    *,
    settings: Settings | None = None,
    llm_backend: LLMBackend | None = None,
    application: LexRAGApplication | None = None,
) -> LexRAGASGIApplication:
    """Create the authenticated ASGI app for deployment."""
    resolved_settings = settings or get_settings()
    resolved_application = application or build_default_application(
        settings=resolved_settings,
        llm_backend=llm_backend,
    )
    return LexRAGASGIApplication(
        application=resolved_application,
        authorizer=RequestAuthorizer(
            api_secret_key=resolved_settings.API_SECRET_KEY,
        ),
        rate_limiter=FixedWindowRateLimiter(
            limit=resolved_settings.RATE_LIMIT_PER_MINUTE,
        ),
    )


def run_server(
    *,
    host: str = "0.0.0.0",
    port: int = 8000,
    app: LexRAGASGIApplication,
) -> int:
    """Run the ASGI serving surface until interrupted."""
    uvicorn = _uvicorn_module()
    uvicorn.run(app, host=host, port=port)
    return 0


def main(
    argv: list[str] | None = None, *, llm_backend: LLMBackend | None = None
) -> int:
    """Parse CLI args, validate runtime safety, and start the ASGI server."""
    args = _parse_args(argv=argv)
    settings = get_settings()
    _validate_startup(settings=settings, llm_backend=llm_backend)
    app = create_app(
        settings=settings,
        llm_backend=llm_backend,
    )
    return run_server(host=args.host, port=args.port, app=app)


def _parse_args(*, argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="lexrag-serve")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args(argv)


def _validate_startup(
    *,
    settings: Settings,
    llm_backend: LLMBackend | None,
) -> None:
    if llm_backend is None:
        raise ValueError("llm_backend must be configured before serving traffic")
    if settings.API_SECRET_KEY is None:
        raise ValueError("API_SECRET_KEY must be set before serving traffic")
    if settings.LEXRAG_USE_REAL_STORES:
        return
    raise ValueError("LEXRAG_USE_REAL_STORES must be true before serving traffic")


def _uvicorn_module():
    try:
        import uvicorn  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "uvicorn is required to run the LexRAG ASGI server"
        ) from exc
    return uvicorn


if __name__ == "__main__":
    raise SystemExit(main())
