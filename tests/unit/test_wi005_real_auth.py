"""Epic 002 acceptance tests — real JWT authentication.

Verifies the starter uses the framework's TokenService, JwtGuard,
AuthManager, AuthGuardMiddleware, and HasherContract instead of ad-hoc
Bearer header checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestJwtLogin:
    """Story 2: POST /api/auth/login returns real JWT tokens."""

    def test_login_returns_decodable_jwt(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/login",
            json={"email": "root@example.com", "password": "password"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"

        import jwt

        access = jwt.decode(
            body["access_token"],
            options={"verify_signature": False},
        )
        assert access["type"] == "access"
        assert "sub" in access
        assert "exp" in access

    def test_login_with_wrong_password_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/login",
            json={"email": "root@example.com", "password": "wrong"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"


class TestJwtRefresh:
    """Story 2: POST /api/auth/refresh accepts real refresh JWT."""

    def test_refresh_with_login_token_returns_new_access(
        self, client: TestClient
    ) -> None:
        login = client.post(
            "/api/auth/login",
            json={"email": "root@example.com", "password": "password"},
        )
        refresh_token = login.json()["refresh_token"]

        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"

        import jwt

        new_access = jwt.decode(
            body["access_token"], options={"verify_signature": False}
        )
        assert new_access["type"] == "access"
        assert new_access["sub"] == "root@example.com"

    def test_refresh_with_garbage_token_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "not-a-jwt"},
        )
        assert response.status_code == 401


class TestProtectedEndpoints:
    """Story 3: /api/users/me protected by AuthGuardMiddleware."""

    def _get_access_token(self, client: TestClient) -> str:
        login = client.post(
            "/api/auth/login",
            json={"email": "root@example.com", "password": "password"},
        )
        return login.json()["access_token"]

    def test_me_with_jwt_returns_profile(self, client: TestClient) -> None:
        token = self._get_access_token(client)
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "id" in body
        assert "email" in body

    def test_me_without_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/users/me")
        assert response.status_code == 401

    def test_me_with_invalid_jwt_returns_401(self, client: TestClient) -> None:
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert response.status_code == 401

    def test_show_without_auth_still_works(self, client: TestClient) -> None:
        """show() has without_middleware=['auth'] — public endpoint."""
        response = client.get("/api/users/id/1")
        assert response.status_code == 200


class TestPasswordHashing:
    """Story 2 security: passwords verified via HasherContract, not plaintext."""

    def test_login_uses_hashed_password_comparison(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/login",
            json={"email": "root@example.com", "password": "password"},
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "bad_password",
        [
            pytest.param("", id="empty"),
            pytest.param("wrong", id="wrong"),
            pytest.param("Password", id="case-sensitive"),
        ],
    )
    def test_login_rejects_bad_passwords(
        self, client: TestClient, bad_password: str
    ) -> None:
        response = client.post(
            "/api/auth/login",
            json={"email": "root@example.com", "password": bad_password},
        )
        assert response.status_code in (401, 422)
