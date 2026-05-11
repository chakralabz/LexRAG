"""Deprecated legacy HTTP handler retained only as a migration shim."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler


class LexRAGRequestHandler(BaseHTTPRequestHandler):
    """Fail fast so deployments do not keep using the retired raw HTTP stack."""

    def __init__(self, *args, **kwargs) -> None:
        _ = args, kwargs
        raise RuntimeError(
            "LexRAGRequestHandler is deprecated; deploy lexrag.serving.server:create_app via an ASGI server"
        )
