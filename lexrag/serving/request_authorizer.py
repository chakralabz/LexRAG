"""Authorization checks for the serving HTTP surface."""

from __future__ import annotations

import hmac
from collections.abc import Mapping


class RequestAuthorizer:
    """Enforce bearer-token authentication on protected routes."""

    def __init__(self, *, api_secret_key: str | None) -> None:
        self.api_secret_key = api_secret_key

    def authorize(self, *, path: str, headers: Mapping[str, str]) -> None:
        if not self._protected(path=path):
            return
        if self.api_secret_key is None:
            raise PermissionError("authorization_unconfigured")
        token = self._bearer_token(headers=headers)
        if token is None:
            raise PermissionError("missing_authorization")
        if hmac.compare_digest(token, self.api_secret_key):
            return
        raise PermissionError("invalid_authorization")

    def _protected(self, *, path: str) -> bool:
        return path not in {"/health", "/ready"}

    def _bearer_token(self, *, headers: Mapping[str, str]) -> str | None:
        authorization = headers.get("authorization")
        if authorization is None or not authorization.startswith("Bearer "):
            return None
        token = authorization.removeprefix("Bearer ").strip()
        return token or None
