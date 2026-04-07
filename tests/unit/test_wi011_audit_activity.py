"""WI-011 tests — Audit and Activity log (Epic 008, Story 7).

Validates Auditable mixin, AuditLog service, ActivityRecorder,
and the new migrations for audit_entries and activity_entries.
"""

from __future__ import annotations

import asyncio
from pathlib import Path


from arvel.audit import AuditAction, AuditEntry, Auditable
from arvel.audit.service import REDACTED, _redact
from arvel.activity import ActivityEntry, ActivityRecorder


class TestAuditableMixin:
    def test_user_has_auditable_mixin(self) -> None:
        from app.models.user import User

        assert issubclass(User, Auditable)

    def test_user_audit_redact_includes_password(self) -> None:
        from app.models.user import User

        assert "password" in User.__audit_redact__

    def test_auditable_default_redact_is_empty(self) -> None:
        assert Auditable.__audit_redact__ == set()


class TestAuditRedaction:
    def test_redact_replaces_sensitive_fields(self) -> None:
        values = {"name": "Alice", "password": "secret123", "email": "a@b.com"}
        result = _redact(values, {"password"})
        assert result["password"] == REDACTED
        assert result["name"] == "Alice"
        assert result["email"] == "a@b.com"

    def test_redact_with_empty_set_returns_original(self) -> None:
        values = {"name": "Alice", "password": "secret123"}
        result = _redact(values, set())
        assert result == values

    def test_redact_multiple_fields(self) -> None:
        values = {"password": "secret", "token": "abc123", "name": "Bob"}
        result = _redact(values, {"password", "token"})
        assert result["password"] == REDACTED
        assert result["token"] == REDACTED
        assert result["name"] == "Bob"


class TestAuditEntryModel:
    def test_audit_entry_tablename(self) -> None:
        assert AuditEntry.__tablename__ == "audit_entries"

    def test_audit_action_enum_values(self) -> None:
        assert AuditAction.CREATED == "created"
        assert AuditAction.UPDATED == "updated"
        assert AuditAction.DELETED == "deleted"


class TestActivityEntryModel:
    def test_activity_entry_tablename(self) -> None:
        assert ActivityEntry.__tablename__ == "activity_entries"


class TestActivityRecorder:
    def test_recorder_fluent_api(self) -> None:
        from unittest.mock import AsyncMock

        session = AsyncMock()
        recorder = ActivityRecorder("users", session=session)
        result = recorder.log("created user").by(type("FakeUser", (), {"id": 1})())
        assert result is recorder
        result2 = result.on(type("FakeSubject", (), {"id": 42})())
        assert result2 is recorder


class TestMigrationFilesExist:
    def test_audit_entries_migration_exists(self) -> None:
        path = (
            Path(__file__).resolve().parents[2]
            / "database"
            / "migrations"
            / "006_create_audit_entries_table.py"
        )
        assert path.exists()

    def test_activity_entries_migration_exists(self) -> None:
        path = (
            Path(__file__).resolve().parents[2]
            / "database"
            / "migrations"
            / "007_create_activity_entries_table.py"
        )
        assert path.exists()


class TestAuditMigrationSchema:
    """Verify audit_entries table is created by metadata.create_all."""

    def test_audit_entries_table_exists_after_schema_creation(
        self, tmp_path: Path
    ) -> None:
        from sqlalchemy import inspect
        from sqlalchemy.ext.asyncio import create_async_engine

        import arvel.audit.entry  # noqa: F401 — register AuditEntry
        from arvel.data import ArvelModel

        db_url = f"sqlite+aiosqlite:///{tmp_path / 'audit_test.sqlite3'}"

        async def _setup() -> list[str]:
            engine = create_async_engine(db_url, echo=False)
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(ArvelModel.metadata.create_all)
                async with engine.connect() as conn:
                    return await conn.run_sync(
                        lambda sync_conn: inspect(sync_conn).get_table_names()
                    )
            finally:
                await engine.dispose()

        tables = asyncio.run(_setup())
        assert "audit_entries" in tables

    def test_activity_entries_table_exists_after_schema_creation(
        self, tmp_path: Path
    ) -> None:
        from sqlalchemy import inspect
        from sqlalchemy.ext.asyncio import create_async_engine

        import arvel.activity.entry  # noqa: F401 — register ActivityEntry
        from arvel.data import ArvelModel

        db_url = f"sqlite+aiosqlite:///{tmp_path / 'activity_test.sqlite3'}"

        async def _setup() -> list[str]:
            engine = create_async_engine(db_url, echo=False)
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(ArvelModel.metadata.create_all)
                async with engine.connect() as conn:
                    return await conn.run_sync(
                        lambda sync_conn: inspect(sync_conn).get_table_names()
                    )
            finally:
                await engine.dispose()

        tables = asyncio.run(_setup())
        assert "activity_entries" in tables
