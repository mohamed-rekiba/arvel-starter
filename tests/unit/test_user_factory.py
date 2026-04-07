"""Unit tests for the user factory."""

from __future__ import annotations

from database.factories.user_factory import make_user


class TestMakeUserDefaults:
    def test_returns_user_with_faker_generated_defaults(self) -> None:
        user = make_user()
        assert user.name is not None
        assert len(user.name) > 0
        assert "@" in user.email
        assert user.password is not None
        assert len(user.password) > 0
        assert user.parent_id is None

    def test_two_calls_produce_different_emails(self) -> None:
        user_a = make_user()
        user_b = make_user()
        assert user_a.email != user_b.email


class TestMakeUserOverrides:
    def test_name_override(self) -> None:
        user = make_user(name="Custom Name")
        assert user.name == "Custom Name"

    def test_email_override(self) -> None:
        user = make_user(email="custom@test.com")
        assert user.email == "custom@test.com"

    def test_password_override_is_hashed(self) -> None:
        user = make_user(password="my-secret-pw")
        assert user.password != "my-secret-pw"
        assert user.password.startswith("$2b$")

    def test_parent_id_override(self) -> None:
        user = make_user(parent_id=42)
        assert user.parent_id == 42

    def test_user_id_override(self) -> None:
        user = make_user(user_id=99)
        assert user.id == 99

    def test_user_id_not_set_when_omitted(self) -> None:
        user = make_user()
        assert not hasattr(user, "id") or user.id is None
