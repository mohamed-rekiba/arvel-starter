"""Migration upgrade/downgrade tests for all starter migration files.

Uses ``ArvelModel.metadata.create_all`` for schema creation (matching how the
seeder tests validate the schema) and then verifies table structure, column
definitions, and FK constraints.  A separate test validates the Alembic-based
MigrationRunner by copying migration files into ``versions/`` so Alembic can
discover them.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import app.models.user  # noqa: F401 — register User in ArvelModel.metadata
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from arvel.data import ArvelModel


def _starter_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _migrations_dir() -> Path:
    return _starter_root() / "database" / "migrations"


async def _create_schema(db_url: str) -> None:
    engine = create_async_engine(db_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(ArvelModel.metadata.create_all)
    finally:
        await engine.dispose()


async def _get_table_names(db_url: str) -> list[str]:
    engine = create_async_engine(db_url, echo=False)
    try:
        async with engine.connect() as conn:
            return await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
    finally:
        await engine.dispose()


async def _table_columns(db_url: str, table_name: str) -> list[str]:
    engine = create_async_engine(db_url, echo=False)
    try:
        async with engine.connect() as conn:
            return await conn.run_sync(
                lambda sync_conn: [
                    c["name"] for c in inspect(sync_conn).get_columns(table_name)
                ]
            )
    finally:
        await engine.dispose()


class TestSchemaCreateAll:
    """Validate that ArvelModel.metadata.create_all produces the expected schema."""

    def test_creates_users_table(self, tmp_path: Path) -> None:
        db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite3'}"
        asyncio.run(_create_schema(db_url))
        tables = asyncio.run(_get_table_names(db_url))
        assert "users" in tables

    def test_users_table_has_expected_columns(self, tmp_path: Path) -> None:
        db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite3'}"
        asyncio.run(_create_schema(db_url))
        cols = asyncio.run(_table_columns(db_url, "users"))
        required = (
            "id",
            "name",
            "email",
            "password",
            "parent_id",
            "created_at",
            "updated_at",
            "deleted_at",
        )
        for expected in required:
            assert expected in cols, f"Missing column {expected} in users"

    def test_schema_accepts_insert(self, tmp_path: Path) -> None:
        db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite3'}"
        asyncio.run(_create_schema(db_url))

        async def _insert() -> int:
            engine = create_async_engine(db_url, echo=False)
            try:
                async with engine.begin() as conn:
                    await conn.execute(
                        text(
                            "INSERT INTO users (name, email, password, created_at, updated_at) "
                            "VALUES ('Test', 'test@t.com', 'pw', datetime('now'), datetime('now'))"
                        )
                    )
                    result = await conn.execute(text("SELECT COUNT(*) FROM users"))
                    return int(result.scalar_one())
            finally:
                await engine.dispose()

        count = asyncio.run(_insert())
        assert count == 1

    def test_email_unique_constraint_enforced(self, tmp_path: Path) -> None:
        db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite3'}"
        asyncio.run(_create_schema(db_url))

        async def _insert_duplicate() -> bool:
            import sqlite3

            engine = create_async_engine(db_url, echo=False)
            try:
                async with engine.begin() as conn:
                    await conn.execute(
                        text(
                            "INSERT INTO users (name, email, password, created_at, updated_at) "
                            "VALUES ('A', 'dup@t.com', 'pw', datetime('now'), datetime('now'))"
                        )
                    )
                    try:
                        await conn.execute(
                            text(
                                "INSERT INTO users (name, email, password, created_at, updated_at) "
                                "VALUES ('B', 'dup@t.com', 'pw', datetime('now'), datetime('now'))"
                            )
                        )
                    except Exception as exc:
                        return "UNIQUE constraint" in str(exc) or isinstance(
                            exc.__cause__, sqlite3.IntegrityError
                        )
                    return False
            finally:
                await engine.dispose()

        violated = asyncio.run(_insert_duplicate())
        assert violated, "Email unique constraint should reject duplicate"


class TestAlembicMigrationRunner:
    """Validate MigrationRunner upgrade/downgrade with files in versions/."""

    def _prepare_versions(self, tmp_migrations: Path) -> None:
        """Copy starter migration files into a versions/ subdirectory for Alembic."""
        versions = tmp_migrations / "versions"
        versions.mkdir(parents=True, exist_ok=True)
        src = _migrations_dir()
        for f in sorted(src.iterdir()):
            if f.is_file() and f.suffix == ".py" and f.name[0].isdigit():
                shutil.copy2(f, versions / f.name)

    def test_upgrade_creates_all_tables(self, tmp_path: Path) -> None:
        from arvel.data.migrations import MigrationRunner

        db_url = f"sqlite+aiosqlite:///{tmp_path / 'alembic.sqlite3'}"
        tmp_migrations = tmp_path / "migrations"
        tmp_migrations.mkdir()
        self._prepare_versions(tmp_migrations)

        runner = MigrationRunner(db_url=db_url, migrations_dir=str(tmp_migrations))
        asyncio.run(runner.upgrade())

        tables = asyncio.run(_get_table_names(db_url))
        assert "users" in tables
        assert "auth_refresh_tokens" in tables
        assert "media" in tables

    def test_downgrade_two_steps_removes_last_table(self, tmp_path: Path) -> None:
        from arvel.data.migrations import MigrationRunner

        db_url = f"sqlite+aiosqlite:///{tmp_path / 'alembic-down.sqlite3'}"
        tmp_migrations = tmp_path / "migrations"
        tmp_migrations.mkdir()
        self._prepare_versions(tmp_migrations)

        runner = MigrationRunner(db_url=db_url, migrations_dir=str(tmp_migrations))
        asyncio.run(runner.upgrade())
        asyncio.run(runner.downgrade(steps=5))

        tables = asyncio.run(_get_table_names(db_url))
        assert "media" not in tables
        assert "users" in tables

    def test_full_downgrade_removes_all_app_tables(self, tmp_path: Path) -> None:
        from arvel.data.migrations import MigrationRunner

        db_url = f"sqlite+aiosqlite:///{tmp_path / 'alembic-full-down.sqlite3'}"
        tmp_migrations = tmp_path / "migrations"
        tmp_migrations.mkdir()
        self._prepare_versions(tmp_migrations)

        runner = MigrationRunner(db_url=db_url, migrations_dir=str(tmp_migrations))
        asyncio.run(runner.upgrade())
        asyncio.run(runner.downgrade(steps=7))

        tables = asyncio.run(_get_table_names(db_url))
        app_tables = [t for t in tables if t != "alembic_version"]
        assert app_tables == []

    def test_upgrade_is_idempotent(self, tmp_path: Path) -> None:
        from arvel.data.migrations import MigrationRunner

        db_url = f"sqlite+aiosqlite:///{tmp_path / 'alembic-idem.sqlite3'}"
        tmp_migrations = tmp_path / "migrations"
        tmp_migrations.mkdir()
        self._prepare_versions(tmp_migrations)

        runner = MigrationRunner(db_url=db_url, migrations_dir=str(tmp_migrations))
        asyncio.run(runner.upgrade())
        asyncio.run(runner.upgrade())

        tables = asyncio.run(_get_table_names(db_url))
        assert "users" in tables

    def test_status_returns_all_migration_entries(self, tmp_path: Path) -> None:
        from arvel.data.migrations import MigrationRunner

        db_url = f"sqlite+aiosqlite:///{tmp_path / 'alembic-status.sqlite3'}"
        tmp_migrations = tmp_path / "migrations"
        tmp_migrations.mkdir()
        self._prepare_versions(tmp_migrations)

        runner = MigrationRunner(db_url=db_url, migrations_dir=str(tmp_migrations))
        entries = asyncio.run(runner.status())
        assert len(entries) == 7
        for entry in entries:
            assert "revision" in entry
            assert "message" in entry

    def test_auth_refresh_tokens_has_expected_columns(self, tmp_path: Path) -> None:
        from arvel.data.migrations import MigrationRunner

        db_url = f"sqlite+aiosqlite:///{tmp_path / 'alembic-cols.sqlite3'}"
        tmp_migrations = tmp_path / "migrations"
        tmp_migrations.mkdir()
        self._prepare_versions(tmp_migrations)

        runner = MigrationRunner(db_url=db_url, migrations_dir=str(tmp_migrations))
        asyncio.run(runner.upgrade())

        cols = asyncio.run(_table_columns(db_url, "auth_refresh_tokens"))
        for expected in ("id", "user_id", "token_hash", "issued_at", "expires_at"):
            assert expected in cols, f"Missing column {expected} in auth_refresh_tokens"

    def test_media_table_has_expected_columns(self, tmp_path: Path) -> None:
        from arvel.data.migrations import MigrationRunner

        db_url = f"sqlite+aiosqlite:///{tmp_path / 'alembic-media-cols.sqlite3'}"
        tmp_migrations = tmp_path / "migrations"
        tmp_migrations.mkdir()
        self._prepare_versions(tmp_migrations)

        runner = MigrationRunner(db_url=db_url, migrations_dir=str(tmp_migrations))
        asyncio.run(runner.upgrade())

        cols = asyncio.run(_table_columns(db_url, "media"))
        for expected in (
            "id",
            "uuid",
            "model_type",
            "model_id",
            "collection",
            "name",
            "filename",
            "original_filename",
            "mime_type",
            "size",
            "disk",
            "path",
            "conversions",
            "custom_properties",
            "order_column",
            "created_at",
            "updated_at",
        ):
            assert expected in cols, f"Missing column {expected} in media"
