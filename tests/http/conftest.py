"""Shared fixtures for HTTP endpoint tests.

Boots the full Arvel application with SQLite and in-memory/fake
infrastructure services, then provides an async TestClient.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from arvel.foundation.application import Application
from arvel.testing import TestClient

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


_STARTER_ROOT = Path(__file__).resolve().parents[2]
_HTTP_DB_PATH = _STARTER_ROOT / ".tests" / "db" / "test_http.db"

_HTTP_TEST_ENV: dict[str, str] = {
    "APP_ENV": "testing",
    "APP_DEBUG": "false",
    "APP_KEY": "test-secret-key-for-starter-demo-only",
    "DB_DRIVER": "sqlite",
    "DB_DATABASE": str(_HTTP_DB_PATH),
    "CACHE_DRIVER": "memory",
    "QUEUE_DRIVER": "sync",
    "MAIL_DRIVER": "log",
    "LOCK_DRIVER": "memory",
    "STORAGE_DRIVER": "local",
    "STORAGE_LOCAL_ROOT": str(_STARTER_ROOT / ".tests" / "storage" / "app"),
    "SEARCH_DRIVER": "collection",
    "BROADCAST_DRIVER": "memory",
    "OBSERVABILITY_LOG_LEVEL": "warning",
}


@pytest.fixture(scope="module", params=["asyncio"], autouse=True)
def anyio_backend(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture(scope="module")
def _set_http_env(monkeypatch_module):
    """Set env vars for the entire HTTP test module."""
    for key, value in _HTTP_TEST_ENV.items():
        monkeypatch_module.setenv(key, value)


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch."""
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="module")
async def app(monkeypatch_module) -> AsyncGenerator[Application]:
    """Boot the full Arvel application once per test module.

    Deletes the previous test DB so each module run starts clean.
    """
    _HTTP_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _HTTP_DB_PATH.unlink(missing_ok=True)
    (_STARTER_ROOT / ".tests" / "storage" / "app").mkdir(parents=True, exist_ok=True)

    for key, value in _HTTP_TEST_ENV.items():
        monkeypatch_module.setenv(key, value)

    application = await Application.create(base_path=_STARTER_ROOT, testing=True)
    yield application
    await application.shutdown()


@pytest.fixture
async def client(app: Application) -> AsyncGenerator[TestClient]:
    """Async TestClient wrapping the booted app."""
    async with TestClient(app.asgi_app()) as c:
        yield c


@pytest.fixture
async def auth_client(app: Application) -> AsyncGenerator[TestClient]:
    """Authenticated TestClient with a pre-created user token.

    Creates a user via login and sets the Bearer token for all requests.
    """
    from arvel.auth.tokens import TokenService
    from arvel.security.config import SecuritySettings
    from arvel.security.hashing import BcryptHasher

    hasher = BcryptHasher(rounds=4)
    settings = SecuritySettings()
    secret = os.environ.get("APP_KEY", "") or "test-secret-key-for-starter-demo-only"
    token_service = TokenService(
        secret,
        algorithm=settings.jwt_algorithm,
        access_ttl_minutes=settings.jwt_access_ttl_minutes,
        refresh_ttl_days=settings.jwt_refresh_ttl_days,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )

    async with TestClient(app.asgi_app()) as c:
        email = f"auth-test-{id(c)}@test.com"
        response = await c.post(
            "/api/users/",
            json={
                "name": "Auth Test User",
                "email": email,
                "password": hasher.make("password123"),
            },
        )
        if response.status_code == 201:
            pair = token_service.create_token_pair(email)
            c.acting_as(headers={"Authorization": f"Bearer {pair['access_token']}"})

        yield c
