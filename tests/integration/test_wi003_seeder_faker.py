"""WI-003 QA-Pre: Faker-based seeder tests.

These tests verify the seeder refactoring requirements:
- FR-01: Faker-generated names/passwords
- FR-02: Idempotency with stable emails
- AC-01.3: Hierarchy preserved
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TypedDict, cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from arvel.data import ArvelModel, SeedRunner


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


async def _run_seed(db_url: str) -> None:
    await _create_schema(db_url)
    seed_runner = SeedRunner(seeders_dir=_seeders_dir(), db_url=db_url)
    await seed_runner.run(environment="testing")


async def _fetch_users(db_url: str) -> list[UserSeedRow]:
    engine = create_async_engine(db_url, echo=False)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT id, name, email, parent_id FROM users ORDER BY id")
            )
            return [
                {
                    "id": cast("int", row["id"]),
                    "name": cast("str", row["name"]),
                    "email": cast("str", row["email"]),
                    "parent_id": cast("int | None", row["parent_id"]),
                }
                for row in result.mappings().all()
            ]
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


class TestFakerSeederEmails:
    """FR-01 AC-01.1: Seeder uses @starter.local domain emails."""

    def test_seeded_users_have_expected_email_domains(self, tmp_path: Path) -> None:
        db_url = f"sqlite+aiosqlite:///{tmp_path / 'faker_emails.sqlite3'}"
        asyncio.run(_run_seed(db_url))
        users = asyncio.run(_fetch_users(db_url))

        allowed_domains = ("@starter.local", "@example.com")
        for user in users:
            assert any(user["email"].endswith(d) for d in allowed_domains), (
                f"Unexpected email domain: {user['email']}"
            )

    def test_seeded_root_email_is_root_at_starter_local(self, tmp_path: Path) -> None:
        db_url = f"sqlite+aiosqlite:///{tmp_path / 'faker_root.sqlite3'}"
        asyncio.run(_run_seed(db_url))
        users = asyncio.run(_fetch_users(db_url))

        emails = [u["email"] for u in users]
        assert "root@starter.local" in emails


class TestFakerSeederNames:
    """FR-01 AC-01.2: Seeder uses Faker-generated names."""

    def test_seeded_names_are_not_email_prefixes(self, tmp_path: Path) -> None:
        """Names should be Faker names, not derived from email addresses."""
        db_url = f"sqlite+aiosqlite:///{tmp_path / 'faker_names.sqlite3'}"
        asyncio.run(_run_seed(db_url))
        users = asyncio.run(_fetch_users(db_url))

        hardcoded_names = {"root", "child-a", "child-b", "grandchild-a1"}
        for user in users:
            assert user["name"].lower() not in hardcoded_names, (
                f"Name '{user['name']}' looks hardcoded, expected Faker-generated"
            )


class TestFakerSeederHierarchy:
    """FR-01 AC-01.3: Hierarchy structure preserved."""

    def test_five_users_seeded(self, tmp_path: Path) -> None:
        db_url = f"sqlite+aiosqlite:///{tmp_path / 'faker_count.sqlite3'}"
        asyncio.run(_run_seed(db_url))
        count = asyncio.run(_count_users(db_url))
        assert count == 5

    def test_root_has_no_parent(self, tmp_path: Path) -> None:
        db_url = f"sqlite+aiosqlite:///{tmp_path / 'faker_root_parent.sqlite3'}"
        asyncio.run(_run_seed(db_url))
        users = asyncio.run(_fetch_users(db_url))

        by_email = {u["email"]: u for u in users}
        assert by_email["root@starter.local"]["parent_id"] is None

    def test_children_point_to_root(self, tmp_path: Path) -> None:
        db_url = f"sqlite+aiosqlite:///{tmp_path / 'faker_children.sqlite3'}"
        asyncio.run(_run_seed(db_url))
        users = asyncio.run(_fetch_users(db_url))

        by_email = {u["email"]: u for u in users}
        root_id = by_email["root@starter.local"]["id"]
        assert by_email["child-a@starter.local"]["parent_id"] == root_id
        assert by_email["child-b@starter.local"]["parent_id"] == root_id

    def test_grandchild_points_to_child_a(self, tmp_path: Path) -> None:
        db_url = f"sqlite+aiosqlite:///{tmp_path / 'faker_grandchild.sqlite3'}"
        asyncio.run(_run_seed(db_url))
        users = asyncio.run(_fetch_users(db_url))

        by_email = {u["email"]: u for u in users}
        child_a_id = by_email["child-a@starter.local"]["id"]
        assert by_email["grandchild-a1@starter.local"]["parent_id"] == child_a_id


class TestFakerSeederRandomization:
    """US-001 AC: Running seeder twice produces different data values."""

    def test_two_separate_seeds_produce_different_names(self, tmp_path: Path) -> None:
        db_a = f"sqlite+aiosqlite:///{tmp_path / 'rand_a.sqlite3'}"
        db_b = f"sqlite+aiosqlite:///{tmp_path / 'rand_b.sqlite3'}"
        asyncio.run(_run_seed(db_a))
        asyncio.run(_run_seed(db_b))

        users_a = asyncio.run(_fetch_users(db_a))
        users_b = asyncio.run(_fetch_users(db_b))

        names_a = sorted(u["name"] for u in users_a)
        names_b = sorted(u["name"] for u in users_b)
        assert names_a != names_b, (
            "Two independent seed runs should produce different Faker-generated names"
        )


class TestFakerSeederIdempotency:
    """FR-02: Seeder is idempotent with new email scheme."""

    def test_double_seed_produces_five_users(self, tmp_path: Path) -> None:
        db_url = f"sqlite+aiosqlite:///{tmp_path / 'faker_idempotent.sqlite3'}"
        asyncio.run(_run_seed(db_url))
        asyncio.run(_run_seed(db_url))
        count = asyncio.run(_count_users(db_url))
        assert count == 5
