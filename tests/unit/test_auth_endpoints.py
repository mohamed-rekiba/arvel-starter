"""Auth controller endpoint tests — login, refresh, forgot/reset password, change password, verify email, logout."""

from __future__ import annotations

from typing import TYPE_CHECKING

from arvel.auth.password_reset import ResetTokenService

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

_SEED_EMAIL = "root@example.com"
_SEED_PASSWORD = "password"  # noqa: S105
_TEST_SECRET = "test-secret-key-for-starter-demo-only"  # noqa: S105


class TestLogin:
    def test_login_with_valid_credentials_returns_tokens(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/auth/login",
            json={"email": _SEED_EMAIL, "password": _SEED_PASSWORD},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    def test_login_with_wrong_password_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/login",
            json={"email": _SEED_EMAIL, "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"

    def test_login_with_nonexistent_email_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/login",
            json={"email": "nobody@nowhere.test", "password": "irrelevant"},
        )
        assert response.status_code == 401


class TestRefresh:
    def test_refresh_with_valid_token_returns_new_pair(
        self, client: TestClient
    ) -> None:
        tokens = client.post(
            "/api/auth/login",
            json={"email": _SEED_EMAIL, "password": _SEED_PASSWORD},
        ).json()
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body

    def test_refresh_with_invalid_token_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401


class TestForgotPassword:
    def test_forgot_password_with_existing_email_returns_message(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": _SEED_EMAIL},
        )
        assert response.status_code == 200
        assert "message" in response.json()

    def test_forgot_password_with_unknown_email_returns_same_message(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "ghost@nowhere.test"},
        )
        assert response.status_code == 200
        assert "message" in response.json()

    def test_forgot_password_does_not_reveal_email_existence(
        self, client: TestClient
    ) -> None:
        resp_exists = client.post(
            "/api/auth/forgot-password",
            json={"email": _SEED_EMAIL},
        )
        resp_missing = client.post(
            "/api/auth/forgot-password",
            json={"email": "ghost@nowhere.test"},
        )
        assert resp_exists.json()["message"] == resp_missing.json()["message"]


class TestResetPassword:
    def test_reset_password_with_valid_token_changes_password(
        self, client: TestClient
    ) -> None:
        # Use seeded user id=1 (root@starter.local) to avoid affecting other tests
        reset_svc = ResetTokenService(_TEST_SECRET)
        token = reset_svc.create_reset_token("1")
        new_password = "newpass12345"
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": token,
                "email": "root@starter.local",
                "password": new_password,
            },
        )
        assert response.status_code == 200
        assert "reset" in response.json()["message"].lower()

        login_resp = client.post(
            "/api/auth/login",
            json={"email": "root@starter.local", "password": new_password},
        )
        assert login_resp.status_code == 200

    def test_reset_password_with_invalid_token_returns_400(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": "bogus:token:abc:def",
                "email": _SEED_EMAIL,
                "password": "newpass123",
            },
        )
        assert response.status_code == 400

    def test_reset_password_with_nonexistent_email_returns_400(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": "any",
                "email": "ghost@nowhere.test",
                "password": "newpass123",
            },
        )
        assert response.status_code == 400


class TestChangePassword:
    def test_change_password_with_correct_current_password_succeeds(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        new_password = "changed12345"
        response = client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={"current_password": _SEED_PASSWORD, "new_password": new_password},
        )
        assert response.status_code == 200
        assert "changed" in response.json()["message"].lower()

        login_resp = client.post(
            "/api/auth/login",
            json={"email": _SEED_EMAIL, "password": new_password},
        )
        assert login_resp.status_code == 200

        # Restore original password so other tests aren't affected
        restore_headers = {
            "Authorization": f"Bearer {login_resp.json()['access_token']}"
        }
        client.post(
            "/api/auth/change-password",
            headers=restore_headers,
            json={"current_password": new_password, "new_password": _SEED_PASSWORD},
        )

    def test_change_password_with_wrong_current_password_returns_400(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={"current_password": "wrongcurrent", "new_password": "newpass12345"},
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    def test_change_password_without_auth_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/change-password",
            json={"current_password": "any", "new_password": "newpass12345"},
        )
        assert response.status_code == 401


class TestVerifyEmail:
    def test_send_verification_returns_message(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.post("/api/auth/verify-email/send", headers=auth_headers)
        assert response.status_code == 200
        assert "message" in response.json()

    def test_send_verification_without_auth_returns_401(
        self, client: TestClient
    ) -> None:
        response = client.post("/api/auth/verify-email/send")
        assert response.status_code == 401

    def test_verify_email_with_valid_token_marks_verified(
        self, client: TestClient
    ) -> None:
        reset_svc = ResetTokenService(_TEST_SECRET)
        # Use seeded user id=2 (child-a@starter.local) for verification
        token = reset_svc.create_verification_token("2")
        response = client.post(
            "/api/auth/verify-email",
            json={"token": token, "email": "child-a@starter.local"},
        )
        assert response.status_code == 200
        assert "verified" in response.json()["message"].lower()

    def test_verify_email_with_invalid_token_returns_400(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/auth/verify-email",
            json={"token": "bogus:token:abc:def", "email": _SEED_EMAIL},
        )
        assert response.status_code == 400

    def test_verify_email_already_verified_returns_already_message(
        self, client: TestClient
    ) -> None:
        # user 2 was verified in the test above (session-scoped app)
        reset_svc = ResetTokenService(_TEST_SECRET)
        token = reset_svc.create_verification_token("2")
        response = client.post(
            "/api/auth/verify-email",
            json={"token": token, "email": "child-a@starter.local"},
        )
        assert response.status_code == 200
        assert "already" in response.json()["message"].lower()

    def test_verify_email_with_nonexistent_email_returns_400(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/auth/verify-email",
            json={"token": "any", "email": "ghost@nowhere.test"},
        )
        assert response.status_code == 400


class TestLogout:
    def test_logout_with_valid_token_returns_message(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = client.post("/api/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()

    def test_logout_without_auth_returns_401(self, client: TestClient) -> None:
        response = client.post("/api/auth/logout")
        assert response.status_code == 401
