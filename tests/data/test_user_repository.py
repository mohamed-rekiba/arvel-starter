"""Tests for UserRepository — CRUD via transaction, find_by_email."""

from __future__ import annotations

from dirty_equals import IsDatetime, IsPositiveInt

from app.models.user import User
from tests._fixtures.factory import create_user


class TestUserRepositoryCreate:
    async def test_create_user_returns_persisted_instance(self, transaction):
        async with transaction:
            user = await transaction.users.create(
                {
                    "name": "Alice",
                    "email": "alice@repo.com",
                    "password": "hashed-pass",
                }
            )
        assert user.id == IsPositiveInt
        assert user.name == "Alice"
        assert user.email == "alice@repo.com"

    async def test_create_user_sets_timestamps(self, transaction):
        async with transaction:
            user = await transaction.users.create(
                {
                    "name": "Bob",
                    "email": "bob@repo.com",
                    "password": "hashed-pass",
                }
            )
        assert user.created_at == IsDatetime
        assert user.updated_at == IsDatetime


class TestUserRepositoryFind:
    async def test_find_existing_user(self, db_session, transaction):
        created = await create_user(
            db_session, name="Charlie", email="charlie@repo.com"
        )
        async with transaction:
            found = await transaction.users.find(created.id)
        assert found.id == created.id
        assert found.name == "Charlie"

    async def test_find_nonexistent_user_raises(self, transaction):
        from arvel.data.exceptions import NotFoundError

        import pytest

        async with transaction:
            with pytest.raises(NotFoundError):
                await transaction.users.find(999999)


class TestUserRepositoryFindByEmail:
    async def test_find_by_email_returns_user(self, db_session):
        from app.repositories.user_repository import UserRepository
        from arvel.data.observer import ObserverRegistry

        user = await create_user(db_session, email="findme@repo.com")
        repo = UserRepository(session=db_session, observer_registry=ObserverRegistry())
        found = await repo.find_by_email("findme@repo.com")
        assert found is not None
        assert found.id == user.id

    async def test_find_by_email_returns_none_for_missing(self, db_session):
        from app.repositories.user_repository import UserRepository
        from arvel.data.observer import ObserverRegistry

        repo = UserRepository(session=db_session, observer_registry=ObserverRegistry())
        found = await repo.find_by_email("nonexistent@repo.com")
        assert found is None


class TestUserRepositoryUpdate:
    async def test_update_user_changes_name(self, db_session, transaction):
        user = await create_user(db_session, name="Before", email="update@repo.com")
        async with transaction:
            updated = await transaction.users.update(user.id, {"name": "After"})
        assert updated.name == "After"


class TestUserRepositoryDelete:
    async def test_delete_user_soft_deletes(self, db_session, transaction):
        user = await create_user(db_session, email="delete@repo.com")
        async with transaction:
            await transaction.users.delete(user.id)
            found = (
                await transaction.users.query()
                .where(User.id == user.id)
                .order_by(User.id)
                .first()
            )
        assert found is None or found.deleted_at is not None
