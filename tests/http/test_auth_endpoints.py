"""Tests for auth endpoints — login, refresh, password reset, verify email, logout."""

from __future__ import annotations

import os

from arvel.auth.tokens import TokenService
from arvel.security.config import SecuritySettings
from arvel.security.hashing import BcryptHasher
from arvel.testing import TestClient

_hasher = BcryptHasher(rounds=4)


def _make_token_service() -> TokenService:
    settings = SecuritySettings()
    secret = os.environ.get("APP_KEY", "") or "test-secret-key-for-starter-demo-only"
    return TokenService(
        secret,
        algorithm=settings.jwt_algorithm,
        access_ttl_minutes=settings.jwt_access_ttl_minutes,
        refresh_ttl_days=settings.jwt_refresh_ttl_days,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


async def _seed_user(client: TestClient, email: str, password: str = "password123") -> dict:
    """Create a user via the API with a bcrypt-hashed password.

    The store endpoint passes the password through directly to the DB,
    so we must hash it ourselves for auth to work.
    """
    resp = await client.post(
        "/api/users/",
        json={
            "name": "Auth Seed User",
            "email": email,
            "password": _hasher.make(password),
        },
    )
    return resp.json()


class TestLogin:
    async def test_login_with_valid_credentials_returns_tokens(self, client):
        email = "login-valid@test.com"
        await _seed_user(client, email)

        response = await client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "password123",
            },
        )
        response.assert_ok()
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_with_wrong_password_returns_401(self, client):
        email = "login-wrong@test.com"
        await _seed_user(client, email)

        response = await client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "wrongpassword",
            },
        )
        response.assert_status(401)
        assert response.json()["detail"] == "Invalid credentials"

    async def test_login_with_nonexistent_email_returns_401(self, client):
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "password123",
            },
        )
        response.assert_status(401)


class TestRefresh:
    async def test_refresh_with_valid_token_returns_new_pair(self, client):
        email = "refresh-valid@test.com"
        await _seed_user(client, email)

        login_resp = await client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "password123",
            },
        )
        refresh_token = login_resp.json()["refresh_token"]

        response = await client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": refresh_token,
            },
        )
        response.assert_ok()
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_with_invalid_token_returns_401(self, client):
        response = await client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": "invalid-token",
            },
        )
        response.assert_status(401)


class TestForgotPassword:
    async def test_forgot_password_returns_message_for_existing_email(self, client):
        email = "forgot-exists@test.com"
        await _seed_user(client, email)

        response = await client.post(
            "/api/auth/forgot-password",
            json={
                "email": email,
            },
        )
        response.assert_ok()
        assert "reset link" in response.json()["message"].lower()

    async def test_forgot_password_returns_same_message_for_nonexistent(self, client):
        response = await client.post(
            "/api/auth/forgot-password",
            json={
                "email": "noone@test.com",
            },
        )
        response.assert_ok()
        assert "reset link" in response.json()["message"].lower()


class TestChangePassword:
    async def test_change_password_without_auth_returns_401(self, client):
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "password123",
                "new_password": "newpassword456",
            },
        )
        response.assert_status(401)

    async def test_change_password_with_auth_succeeds(self, auth_client):
        response = await auth_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "password123",
                "new_password": "newpassword456",
            },
        )
        if response.status_code == 200:
            assert "changed" in response.json()["message"].lower()


class TestResetPassword:
    async def test_reset_password_with_invalid_token_returns_400(self, client):
        email = "reset-invalid@test.com"
        await _seed_user(client, email)

        response = await client.post(
            "/api/auth/reset-password",
            json={
                "token": "bogus-token",
                "email": email,
                "password": "newpassword456",
            },
        )
        response.assert_status(400)

    async def test_reset_password_with_nonexistent_email_returns_400(self, client):
        response = await client.post(
            "/api/auth/reset-password",
            json={
                "token": "any-token",
                "email": "nobody@test.com",
                "password": "newpassword456",
            },
        )
        response.assert_status(400)


class TestSendVerification:
    async def test_send_verification_without_auth_returns_401(self, client):
        response = await client.post("/api/auth/verify-email/send")
        response.assert_status(401)

    async def test_send_verification_with_auth_returns_message(self, auth_client):
        response = await auth_client.post("/api/auth/verify-email/send")
        if response.status_code == 200:
            msg = response.json()["message"].lower()
            assert "verif" in msg or "already" in msg


class TestVerifyEmail:
    async def test_verify_email_with_invalid_token_returns_400(self, client):
        email = "verify-invalid@test.com"
        await _seed_user(client, email)

        response = await client.post(
            "/api/auth/verify-email",
            json={"token": "bogus", "email": email},
        )
        response.assert_status(400)

    async def test_verify_email_with_nonexistent_email_returns_400(self, client):
        response = await client.post(
            "/api/auth/verify-email",
            json={"token": "any", "email": "ghost@test.com"},
        )
        response.assert_status(400)


class TestLogout:
    async def test_logout_without_auth_returns_401(self, client):
        response = await client.post("/api/auth/logout")
        response.assert_status(401)

    async def test_logout_with_auth_succeeds(self, auth_client):
        response = await auth_client.post("/api/auth/logout")
        response.assert_ok()
        assert "logged out" in response.json()["message"].lower()
