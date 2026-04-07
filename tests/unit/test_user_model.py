"""Unit tests for User model definition and ORM metadata."""

from __future__ import annotations

from app.models.user import User


class TestUserModelShape:
    def test_user_construction_with_required_fields(self) -> None:
        user = User(id=1, name="Jane", email="jane@example.com", password="pw-example")
        assert user.name == "Jane"
        assert user.email == "jane@example.com"
        assert user.password == "pw-example"

    def test_parent_id_defaults_to_none(self) -> None:
        user = User(id=1, name="Jane", email="jane@example.com", password="pw-example")
        assert user.parent_id is None

    def test_parent_id_can_be_set(self) -> None:
        user = User(
            id=2, name="Child", email="child@example.com", password="pw", parent_id=1
        )
        assert user.parent_id == 1


class TestUserFillable:
    def test_fillable_contains_expected_fields(self) -> None:
        assert User.__fillable__ == {"name", "email", "password", "parent_id"}

    def test_id_is_not_fillable(self) -> None:
        assert "id" not in User.__fillable__


class TestUserTableMetadata:
    def test_tablename_is_users(self) -> None:
        assert User.__tablename__ == "users"

    def test_email_column_is_unique(self) -> None:
        email_col = User.__table__.columns["email"]
        assert email_col.unique is True

    def test_parent_id_column_is_nullable(self) -> None:
        parent_col = User.__table__.columns["parent_id"]
        assert parent_col.nullable is True

    def test_parent_id_column_is_indexed(self) -> None:
        parent_col = User.__table__.columns["parent_id"]
        assert parent_col.index is True

    def test_id_is_primary_key(self) -> None:
        id_col = User.__table__.columns["id"]
        assert id_col.primary_key is True

    def test_parent_id_column_type_allows_none(self) -> None:
        user = User(id=1, name="Test", email="t@t.com", password="pw", parent_id=None)
        assert user.parent_id is None
