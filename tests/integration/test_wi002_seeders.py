from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from arvel.data import ArvelModel, SeedRunner
from arvel.data.seeder import discover_seeders
from arvel.foundation.application import Application

if TYPE_CHECKING:
    import pytest


class UserSeedRow(TypedDict):
    id: int
    name: str
    email: str
    parent_id: int | None


def _starter_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _seeders_dir() -> Path:
    return _starter_root() / "database" / "seeders"


async def _create_schema(db_url: str) -> None:
    engine = create_async_engine(db_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(ArvelModel.metadata.create_all)
    finally:
        await engine.dispose()


async def _run_migrations_and_seed(db_url: str) -> None:
    await _create_schema(db_url)
    seed_runner = SeedRunner(seeders_dir=_seeders_dir(), db_url=db_url)
    await seed_runner.run(environment="testing")


async def _fetch_users(db_url: str) -> list[UserSeedRow]:
    engine = create_async_engine(db_url, echo=False)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    """
                    SELECT id, name, email, parent_id
                    FROM users
                    ORDER BY id
                    """
                )
            )
            rows: list[UserSeedRow] = []
            for row in result.mappings().all():
                rows.append(
                    {
                        "id": cast("int", row["id"]),
                        "name": cast("str", row["name"]),
                        "email": cast("str", row["email"]),
                        "parent_id": cast("int | None", row["parent_id"]),
                    }
                )
            return rows
    finally:
        await engine.dispose()


async def _count_users(db_url: str) -> int:
    engine = create_async_engine(db_url, echo=False)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) AS count FROM users"))
            return int(result.scalar_one())
    finally:
        await engine.dispose()


def test_seed_discovery_finds_database_seeder() -> None:
    names = [seeder.__name__ for seeder in discover_seeders(_seeders_dir())]
    if names != ["DatabaseSeeder"]:
        raise AssertionError(f"Expected only DatabaseSeeder entrypoint, got {names}")


def test_seeders_populate_wi002_hierarchy(tmp_path: Path) -> None:
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'seeded.sqlite3'}"
    asyncio.run(_run_migrations_and_seed(db_url))
    users = asyncio.run(_fetch_users(db_url))

    if len(users) != 5:
        raise AssertionError(f"Expected exactly 5 seeded users, found {len(users)}")

    users_by_email = {str(row["email"]): row for row in users}
    root_id = users_by_email["root@starter.local"]["id"]
    child_a_id = users_by_email["child-a@starter.local"]["id"]

    if users_by_email["root@starter.local"]["parent_id"] is not None:
        raise AssertionError("Root user must not have a parent_id")
    if users_by_email["child-a@starter.local"]["parent_id"] != root_id:
        raise AssertionError("Child A should be attached to Root User")
    if users_by_email["child-b@starter.local"]["parent_id"] != root_id:
        raise AssertionError("Child B should be attached to Root User")
    if users_by_email["grandchild-a1@starter.local"]["parent_id"] != child_a_id:
        raise AssertionError("Grandchild A1 should be attached to Child A")


def test_seeders_are_idempotent(tmp_path: Path) -> None:
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'idempotent.sqlite3'}"
    asyncio.run(_run_migrations_and_seed(db_url))
    asyncio.run(_run_migrations_and_seed(db_url))

    seeded_count = asyncio.run(_count_users(db_url))
    if seeded_count != 5:
        raise AssertionError(f"Seeder rerun must keep 5 users, found {seeded_count}")


def test_seeded_identity_works_with_auth_flow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'app-seeded.sqlite3'}"
    asyncio.run(_run_migrations_and_seed(db_url))

    monkeypatch.setenv("DB_URL", db_url)
    app = asyncio.run(Application.create(_starter_root(), testing=True))
    try:
        from fastapi.testclient import TestClient

        client = TestClient(app.asgi_app())
        login_response = client.post(
            "/api/auth/login",
            json={"email": "root@starter.local", "password": "password"},
        )
        if login_response.status_code != 200:
            raise AssertionError(
                f"Seeded root login should succeed, got {login_response.status_code}"
            )

        access_token = login_response.json()["access_token"]
        me_response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if me_response.status_code != 200:
            raise AssertionError(
                f"/api/users/me should accept seeded root token, got {me_response.status_code}"
            )
        if me_response.json()["email"] != "root@starter.local":
            raise AssertionError(
                "Expected /api/users/me to resolve seeded root identity"
            )
    finally:
        asyncio.run(app.shutdown())
