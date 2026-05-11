from __future__ import annotations

import pytest

from lexrag.config.config import Settings, _validate_runtime_security


def test_runtime_security_allows_missing_secret_outside_prod() -> None:
    settings = Settings(LEXRAG_ENV="DEV", API_SECRET_KEY=None)

    _validate_runtime_security(settings)


def test_runtime_security_requires_secret_in_prod() -> None:
    settings = Settings(LEXRAG_ENV="PROD", API_SECRET_KEY=None)

    with pytest.raises(ValueError, match="API_SECRET_KEY"):
        _validate_runtime_security(settings)
