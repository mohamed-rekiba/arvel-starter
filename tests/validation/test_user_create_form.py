"""Tests for UserCreateFormRequest — rules, uniqueness, after_validation."""

from __future__ import annotations

from app.http.requests.user_create_request import UserCreateFormRequest


class TestUserCreateFormRules:
    def test_authorize_returns_true(self):
        form = UserCreateFormRequest()
        assert form.authorize(None) is True

    def test_rules_include_name_email_password(self):
        form = UserCreateFormRequest()
        rules = form.rules()
        assert "name" in rules
        assert "email" in rules
        assert "password" in rules

    def test_rules_without_session_has_no_unique_rule(self):
        form = UserCreateFormRequest()
        rules = form.rules()
        email_rules = rules["email"]
        rule_types = [type(r).__name__ for r in email_rules]
        assert "Unique" not in rule_types

    def test_rules_with_session_includes_unique_rule(self, db_session):
        form = UserCreateFormRequest(session=db_session)
        rules = form.rules()
        email_rules = rules["email"]
        rule_types = [type(r).__name__ for r in email_rules]
        assert "Unique" in rule_types


class TestUserCreateFormAfterValidation:
    def test_after_validation_lowercases_email(self):
        form = UserCreateFormRequest()
        data = {
            "name": "Alice",
            "email": "  ALICE@TEST.COM  ",
            "password": "password123",
        }
        result = form.after_validation(data)
        assert result["email"] == "alice@test.com"

    def test_after_validation_handles_missing_email(self):
        form = UserCreateFormRequest()
        data = {"name": "Alice", "password": "password123"}
        result = form.after_validation(data)
        assert "email" not in result


class TestUserCreateFormMessages:
    def test_messages_include_required_fields(self):
        form = UserCreateFormRequest()
        messages = form.messages()
        assert "name._Required" in messages
        assert "email._Required" in messages
        assert "password._Required" in messages

    def test_messages_include_unique_email(self):
        form = UserCreateFormRequest()
        messages = form.messages()
        assert "email.Unique" in messages
