"""Story 8: Transaction with nested savepoints — demonstrates the pattern.

Shows how ``Transaction`` wraps a session with observer dispatch,
and how ``nested()`` savepoints allow partial rollback while keeping
the outer transaction intact.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from arvel.data import ArvelModel, ObserverRegistry, Transaction
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.user import User
from app.observers.user_observer import UserObserver
from app.repositories.user_repository import UserRepository

if TYPE_CHECKING:
    pass


_TEST_DB = Path(__file__).resolve().parents[2] / "database" / "database.sqlite"


@pytest.fixture
def _db_url() -> str:
    return f"sqlite+aiosqlite:///{_TEST_DB}"


def _unique_email(prefix: str = "tx") -> str:
    return f"{prefix}-{uuid.uuid7().hex[:8]}@tx-test.com"


class _AppTransaction(Transaction):
    """Typed transaction with a ``users`` property for full type safety."""

    @property
    def users(self) -> UserRepository:
        return self._get_repo(UserRepository)


class TestTransactionNestedSavepoints:
    """Demonstrates Transaction + nested() savepoint pattern.

    The nested savepoint rolls back a child operation when it raises,
    while the outer transaction's parent user creation persists.
    """

    def test_nested_savepoint_rolls_back_child_preserves_parent(
        self,
        _db_url: str,
    ) -> None:
        parent_email = _unique_email("parent")
        child_email = _unique_email("child")

        async def _run() -> tuple[bool, bool]:
            engine = create_async_engine(_db_url)
            async with engine.begin() as conn:
                async with AsyncSession(bind=conn, expire_on_commit=False) as session:
                    registry = ObserverRegistry()
                    registry.register(User, UserObserver())

                    tx = _AppTransaction(
                        session=session,
                        observer_registry=registry,
                    )
                    async with tx:
                        await tx.users.create(
                            {
                                "name": "Parent",
                                "email": parent_email,
                                "password": "pw",
                            }
                        )

                        try:
                            async with tx.nested():
                                await tx.users.create(
                                    {
                                        "name": "Child",
                                        "email": child_email,
                                        "password": "pw",
                                    }
                                )
                                msg = "Simulated error in nested savepoint"
                                raise RuntimeError(msg)
                        except RuntimeError:
                            pass

                    parent_row = (
                        await session.execute(
                            ArvelModel.metadata.tables["users"]
                            .select()
                            .where(
                                ArvelModel.metadata.tables["users"].c.email
                                == parent_email
                            ),
                        )
                    ).first()

                    child_row = (
                        await session.execute(
                            ArvelModel.metadata.tables["users"]
                            .select()
                            .where(
                                ArvelModel.metadata.tables["users"].c.email
                                == child_email
                            ),
                        )
                    ).first()

            await engine.dispose()
            return (parent_row is not None, child_row is not None)

        parent_exists, child_exists = asyncio.run(_run())
        assert parent_exists, "Parent user should survive the nested rollback"
        assert not child_exists, "Child user should be rolled back"

    def test_observer_fires_during_transaction_create(
        self,
        _db_url: str,
    ) -> None:
        email = _unique_email("obs-tx")

        async def _run() -> str | None:
            engine = create_async_engine(_db_url)
            async with engine.begin() as conn:
                async with AsyncSession(bind=conn, expire_on_commit=False) as session:
                    registry = ObserverRegistry()
                    registry.register(User, UserObserver())

                    tx = _AppTransaction(
                        session=session,
                        observer_registry=registry,
                    )
                    async with tx:
                        user = await tx.users.create(
                            {
                                "name": "ObsUser",
                                "email": email.upper(),
                                "password": "pw",
                            }
                        )
                        return user.email

            await engine.dispose()
            return None

        result_email = asyncio.run(_run())
        assert result_email is not None
        assert result_email == result_email.lower(), "Observer should normalise email"
