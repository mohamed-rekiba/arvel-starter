"""Shared fixtures for the arvel-starter test suite.

Provides clean environment isolation, automatic anyio/db markers, and
temporary project scaffolding for CLI-level tests.
"""

from __future__ import annotations

import inspect
import os

import pytest

_SETTINGS_ENV_PREFIXES = (
    "APP_",
    "BROADCAST_",
    "CACHE_",
    "DB_",
    "HTTP_",
    "LOCK_",
    "MAIL_",
    "MEDIA_",
    "NOTIFICATION_",
    "OBSERVABILITY_",
    "OIDC_",
    "QUEUE_",
    "SCHEDULER_",
    "SEARCH_",
    "SECURITY_",
    "STORAGE_",
)

_TEST_ENV_OVERRIDES: dict[str, str] = {
    "APP_ENV": "testing",
    "APP_DEBUG": "false",
    "DB_DRIVER": "sqlite",
    "CACHE_DRIVER": "memory",
    "QUEUE_DRIVER": "sync",
    "MAIL_DRIVER": "log",
    "LOCK_DRIVER": "memory",
    "STORAGE_DRIVER": "local",
    "SEARCH_DRIVER": "collection",
    "BROADCAST_DRIVER": "memory",
    "STORAGE_LOCAL_ROOT": ".tests/storage/app",
    "OBSERVABILITY_LOG_CHANNEL_PATHS": """{
        "single": ".tests/storage/logs/app.log",
        "daily": ".tests/storage/logs/app-daily.log"
    }""",
}

_DB_TEST_DIRS = ("/data/", "/validation/")


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove Docker/service env vars, then inject test-specific overrides."""
    for key in list(os.environ):
        if key.startswith(_SETTINGS_ENV_PREFIXES):
            monkeypatch.delenv(key)
    for key, value in _TEST_ENV_OVERRIDES.items():
        monkeypatch.setenv(key, value)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-mark async tests with anyio and DB tests with the db marker."""
    anyio_marker = pytest.mark.anyio
    db_marker = pytest.mark.db
    for item in items:
        fspath = str(item.fspath)
        if item.get_closest_marker("anyio") is None and hasattr(item, "function"):
            fn = item.function
            if hasattr(fn, "__wrapped__") or inspect.iscoroutinefunction(fn):
                item.add_marker(anyio_marker)
        if (
            any(d in fspath for d in _DB_TEST_DIRS)
            and item.get_closest_marker("db") is None
        ):
            item.add_marker(db_marker)
