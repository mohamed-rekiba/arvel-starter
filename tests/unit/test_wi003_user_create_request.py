"""WI-003 QA-Pre: UserCreateRequest type completeness tests.

Tests verify FR-04: UserCreateRequest has email and password fields.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from app.http.resources.user_resource import UserCreateRequest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestUserCreateRequestFields:
    """FR-04 AC-04.1: UserCreateRequest has name, email, password."""

    def test_valid_full_payload_accepted(self) -> None:
        req = UserCreateRequest(
            name="Alice", email="alice@test.com", password="securepass"
        )
        assert req.name == "Alice"
        assert req.email == "alice@test.com"
        assert req.password == "securepass"

    def test_missing_email_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            UserCreateRequest.model_validate(
                {
                    "name": "Alice",
                    "password": "securepass",
                }
            )

    def test_missing_password_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            UserCreateRequest.model_validate(
                {
                    "name": "Alice",
                    "email": "alice@test.com",
                }
            )

    def test_email_too_short_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            UserCreateRequest(name="Alice", email="ab", password="securepass")

    def test_password_too_short_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            UserCreateRequest(name="Alice", email="alice@test.com", password="short")


class TestStoreEndpointWithFullPayload:
    """FR-04 AC-04.3: Store endpoint accepts complete payload."""

    def test_store_with_full_payload_returns_201(self, client: TestClient) -> None:
        response = client.post(
            "/api/users",
            json={
                "name": "Bob",
                "email": f"bob-{__import__('uuid').uuid7().hex[:8]}@test.com",
                "password": "securepass",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Bob"
        assert "id" in body

    def test_store_with_name_only_returns_422(self, client: TestClient) -> None:
        """After adding email/password as required, name-only should fail."""
        response = client.post("/api/users", json={"name": "Alice"})
        assert response.status_code == 422
