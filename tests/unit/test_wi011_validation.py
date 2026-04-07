"""WI-011 tests — FormRequest validation (Epic 008, Story 3).

Validates UserCreateFormRequest, Unique rule, and the /users/validated endpoint.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def _unique_email(prefix: str = "val") -> str:
    return f"{prefix}-{uuid.uuid7().hex[:8]}@test.com"


class TestValidatedEndpoint:
    """Tests for POST /api/users/validated using FormRequest."""

    def test_valid_data_creates_user(self, client: TestClient) -> None:
        response = client.post(
            "/api/users/validated",
            json={
                "name": "Valid User",
                "email": _unique_email(),
                "password": "securepass",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Valid User"
        assert "id" in body

    def test_missing_name_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/users/validated",
            json={"email": _unique_email(), "password": "securepass"},
        )
        assert response.status_code == 422

    def test_missing_email_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/users/validated",
            json={"name": "Test", "password": "securepass"},
        )
        assert response.status_code == 422

    def test_missing_password_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/users/validated",
            json={"name": "Test", "email": _unique_email()},
        )
        assert response.status_code == 422

    def test_short_password_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/users/validated",
            json={"name": "Test", "email": _unique_email(), "password": "short"},
        )
        assert response.status_code == 422

    def test_empty_body_returns_422(self, client: TestClient) -> None:
        response = client.post("/api/users/validated", json={})
        assert response.status_code == 422

    def test_validation_error_includes_field_details(self, client: TestClient) -> None:
        response = client.post(
            "/api/users/validated",
            json={"name": "", "email": "", "password": ""},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["title"] == "Validation Error"
        assert "errors" in body
        assert len(body["errors"]) > 0
        fields_with_errors = {e["field"] for e in body["errors"]}
        assert "name" in fields_with_errors


class TestFormRequestDirect:
    """Direct unit tests for UserCreateFormRequest."""

    @pytest.mark.anyio
    async def test_form_request_authorize_returns_true(self) -> None:
        from app.http.requests.user_create_request import UserCreateFormRequest

        form = UserCreateFormRequest(session=None)
        assert form.authorize(None) is True

    @pytest.mark.anyio
    async def test_form_request_rules_has_name_email_password(self) -> None:
        from app.http.requests.user_create_request import UserCreateFormRequest

        form = UserCreateFormRequest(session=None)
        rules = form.rules()
        assert "name" in rules
        assert "email" in rules
        assert "password" in rules

    @pytest.mark.anyio
    async def test_after_validation_lowercases_email(self) -> None:
        from app.http.requests.user_create_request import UserCreateFormRequest

        form = UserCreateFormRequest(session=None)
        result = form.after_validation(
            {
                "name": "Test",
                "email": "Test@EXAMPLE.COM",
                "password": "secret123",
            }
        )
        assert result["email"] == "test@example.com"

    @pytest.mark.anyio
    async def test_validation_fails_for_missing_required_fields(self) -> None:
        from arvel.validation.exceptions import ValidationError

        from app.http.requests.user_create_request import UserCreateFormRequest

        form = UserCreateFormRequest(session=None)
        with pytest.raises((ValidationError, ValueError)):
            await form.validate_request(request=None, data={})


class TestValidatorEngine:
    """Unit tests for the core Validator class."""

    @pytest.mark.anyio
    async def test_validator_raises_on_failed_rules(self) -> None:
        from arvel.validation.exceptions import ValidationError
        from arvel.validation.validator import Validator

        class Required:
            def passes(
                self, attribute: str, value: object, data: dict[str, object]
            ) -> bool:
                return value is not None and str(value).strip() != ""

            def message(self) -> str:
                return "This field is required."

        validator = Validator()
        with pytest.raises(ValidationError) as exc_info:
            await validator.validate({"name": ""}, {"name": [Required()]})
        assert len(exc_info.value.errors) == 1
        assert exc_info.value.errors[0].field == "name"

    @pytest.mark.anyio
    async def test_validator_passes_on_valid_data(self) -> None:
        from arvel.validation.validator import Validator

        class AlwaysPass:
            def passes(
                self, attribute: str, value: object, data: dict[str, object]
            ) -> bool:
                return True

            def message(self) -> str:
                return ""

        validator = Validator()
        result = await validator.validate({"name": "Alice"}, {"name": [AlwaysPass()]})
        assert result == {"name": "Alice"}
