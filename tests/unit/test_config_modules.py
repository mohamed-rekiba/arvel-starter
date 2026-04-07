"""Config module tests — verify settings classes load and have correct defaults."""

from __future__ import annotations

from typing import TYPE_CHECKING

from config.app import AppSettings

if TYPE_CHECKING:
    import pytest
from config.auth import AuthSettings
from config.cache import CacheSettings
from config.database import DatabaseSettings
from config.mail import MailSettings
from config.observability import ObservabilitySettings
from config.queue import QueueSettings
from config.search import SearchSettings
from config.security import SecuritySettings
from config.session import SessionSettings
from config.storage import StorageSettings


class TestAppSettings:
    def test_default_app_name(self) -> None:
        s = AppSettings()
        assert s.app_name == "Arvel"

    def test_default_env_is_development(self) -> None:
        s = AppSettings()
        assert s.app_env == "development"

    def test_debug_disabled_by_default(self) -> None:
        s = AppSettings()
        assert s.app_debug is False


class TestDatabaseSettings:
    def test_default_driver_is_sqlite(self) -> None:
        s = DatabaseSettings()
        assert s.driver == "sqlite"

    def test_sqlite_url_generation(self) -> None:
        s = DatabaseSettings(driver="sqlite", database="test.db")
        assert s.url.startswith("sqlite+aiosqlite:///")
        assert "test.db" in s.url

    def test_pgsql_url_generation(self) -> None:
        s = DatabaseSettings(
            driver="pgsql", host="db-host", port=5432, database="mydb", username="user"
        )
        url = s.url
        assert "postgresql+asyncpg://" in url
        assert "db-host:5432/mydb" in url

    def test_explicit_db_url_takes_precedence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DB_URL", "postgresql+asyncpg://custom/db")
        s = DatabaseSettings(driver="sqlite")
        assert s.url == "postgresql+asyncpg://custom/db"

    def test_pool_defaults(self) -> None:
        s = DatabaseSettings()
        assert s.pool_size == 10
        assert s.pool_pre_ping is True
        assert s.expire_on_commit is False


class TestAuthSettings:
    def test_default_guard_is_api(self) -> None:
        s = AuthSettings()
        assert s.default_guard == "api"

    def test_guards_contain_api_and_api_key(self) -> None:
        s = AuthSettings()
        assert "api" in s.guards
        assert "api_key" in s.guards


class TestCacheSettings:
    def test_default_driver_is_memory(self) -> None:
        s = CacheSettings()
        assert s.driver == "memory"

    def test_default_ttl(self) -> None:
        s = CacheSettings()
        assert s.default_ttl == 3600


class TestQueueSettings:
    def test_default_driver_is_sync(self) -> None:
        s = QueueSettings()
        assert s.driver == "sync"

    def test_default_queue_name(self) -> None:
        s = QueueSettings()
        assert s.default == "default"


class TestMailSettings:
    def test_default_driver_is_log(self) -> None:
        s = MailSettings()
        assert s.driver == "log"

    def test_default_from_address(self) -> None:
        s = MailSettings()
        assert s.from_address == "noreply@localhost"


class TestStorageSettings:
    def test_default_driver_is_local(self) -> None:
        s = StorageSettings()
        assert s.driver == "local"


class TestSessionSettings:
    def test_default_driver_is_memory(self) -> None:
        s = SessionSettings()
        assert s.driver == "memory"

    def test_default_lifetime(self) -> None:
        s = SessionSettings()
        assert s.lifetime == 120


class TestSecuritySettings:
    def test_default_hash_driver(self) -> None:
        s = SecuritySettings()
        assert s.hash_driver == "bcrypt"

    def test_default_jwt_algorithm(self) -> None:
        s = SecuritySettings()
        assert s.jwt_algorithm == "HS256"


class TestObservabilitySettings:
    def test_default_log_level(self) -> None:
        s = ObservabilitySettings()
        assert s.log_level == "info"

    def test_default_channel_is_stderr(self) -> None:
        s = ObservabilitySettings()
        assert s.log_default_channel == "stderr"

    def test_redact_patterns_include_password(self) -> None:
        s = ObservabilitySettings()
        assert "password" in s.log_redact_patterns


class TestSearchSettings:
    def test_default_provider_is_meilisearch(self) -> None:
        s = SearchSettings()
        assert s.provider == "meilisearch"

    def test_default_port(self) -> None:
        s = SearchSettings()
        assert s.port == 7700
