"""Tests for the User model — metadata, fillable, soft deletes, hierarchy."""

from __future__ import annotations

from dirty_equals import IsDatetime, IsPositiveInt

from app.models.user import User
from tests._fixtures.factory import create_user, make_user


class TestUserModelMetadata:
    def test_tablename_is_users(self):
        assert User.__tablename__ == "users"

    def test_fillable_fields(self):
        expected = {"name", "email", "password", "parent_id"}
        assert User.__fillable__ == expected

    def test_searchable_columns(self):
        assert User.__searchable__ == ["name", "email"]

    def test_audit_redact_password(self):
        assert "password" in User.__audit_redact__


class TestUserModelInstance:
    def test_make_user_has_required_fields(self):
        user = make_user(name="Alice", email="alice@test.com")
        assert user.name == "Alice"
        assert user.email == "alice@test.com"
        assert user.password is not None

    def test_make_user_generates_sequential_emails(self):
        u1 = make_user()
        u2 = make_user()
        assert u1.email != u2.email


class TestUserModelPersistence:
    async def test_create_user_assigns_id(self, db_session):
        user = await create_user(db_session, name="Bob", email="bob@test.com")
        assert user.id == IsPositiveInt

    async def test_create_user_sets_timestamps(self, db_session):
        user = await create_user(db_session)
        assert user.created_at == IsDatetime
        assert user.updated_at == IsDatetime

    async def test_create_user_with_parent(self, db_session):
        parent = await create_user(db_session, name="Parent")
        child = await create_user(db_session, parent_id=parent.id)
        assert child.parent_id == parent.id

    async def test_email_verified_at_defaults_to_none(self, db_session):
        user = await create_user(db_session)
        assert user.email_verified_at is None

    async def test_nullable_parent_id(self, db_session):
        user = await create_user(db_session)
        assert user.parent_id is None
