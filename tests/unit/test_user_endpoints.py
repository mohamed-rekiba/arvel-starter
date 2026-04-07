"""User controller endpoint tests — index, store, show, me, profile-image, hierarchy."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def _unique_email(prefix: str = "test") -> str:
    return f"{prefix}-{uuid.uuid7().hex[:8]}@test.com"


class TestUserIndex:
    def test_index_returns_paginated_list(self, client: TestClient) -> None:
        response = client.get("/api/users")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "pagination" in body
        assert isinstance(body["data"], list)
        assert len(body["data"]) >= 1
        assert "id" in body["data"][0]
        assert "name" in body["data"][0]

    def test_index_pagination_metadata_is_correct(self, client: TestClient) -> None:
        response = client.get("/api/users?page=1&per_page=2")
        assert response.status_code == 200
        body = response.json()
        pag = body["pagination"]
        assert pag["page"] == 1
        assert pag["per_page"] == 2
        assert pag["total"] >= 1
        assert "last_page" in pag
        assert "has_more" in pag
        assert len(body["data"]) <= 2

    def test_index_per_page_capped_at_100(self, client: TestClient) -> None:
        response = client.get("/api/users?per_page=200")
        assert response.status_code == 422


class TestUserStore:
    def test_store_creates_user_and_returns_201(self, client: TestClient) -> None:
        response = client.post(
            "/api/users",
            json={
                "name": "Alice",
                "email": _unique_email("alice"),
                "password": "securepass",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Alice"
        assert "id" in body

    def test_store_with_empty_name_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/users",
            json={"name": "", "email": _unique_email(), "password": "securepass"},
        )
        assert response.status_code == 422

    def test_store_with_long_name_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/users",
            json={
                "name": "x" * 101,
                "email": _unique_email(),
                "password": "securepass",
            },
        )
        assert response.status_code == 422

    def test_store_with_missing_name_returns_422(self, client: TestClient) -> None:
        response = client.post("/api/users", json={})
        assert response.status_code == 422


class TestUserShow:
    def test_show_returns_user_by_id(self, client: TestClient) -> None:
        response = client.get("/api/users/id/1")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == 1
        assert "name" in body

    def test_show_with_zero_id_returns_422(self, client: TestClient) -> None:
        response = client.get("/api/users/id/0")
        assert response.status_code == 422

    def test_show_with_negative_id_returns_422(self, client: TestClient) -> None:
        response = client.get("/api/users/id/-1")
        assert response.status_code == 422


class TestUserMe:
    def test_me_with_valid_bearer_returns_profile(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/users/me", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "root@example.com"
        assert "id" in body

    def test_me_without_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/users/me")
        assert response.status_code == 401

    def test_me_with_invalid_bearer_returns_401(self, client: TestClient) -> None:
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


class TestProfileImageUpload:
    def test_upload_valid_image_returns_url(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/users/me/profile-image",
            headers=auth_headers,
            files={"file": ("photo.png", b"\x89PNG\r\n", "image/png")},
        )
        assert response.status_code == 200
        assert "url" in response.json()

    def test_upload_non_image_mime_returns_400(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/users/me/profile-image",
            headers=auth_headers,
            files={"file": ("doc.txt", b"plain text", "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_without_auth_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/users/me/profile-image",
            files={"file": ("photo.png", b"\x89PNG\r\n", "image/png")},
        )
        assert response.status_code == 401

    def test_upload_with_invalid_bearer_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/users/me/profile-image",
            headers={"Authorization": "Bearer bad-token"},
            files={"file": ("photo.png", b"\x89PNG\r\n", "image/png")},
        )
        assert response.status_code == 401


class TestNotify:
    def test_notify_returns_sent_status(self, client: TestClient) -> None:
        response = client.post("/api/users/1/notify")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "sent"
        assert body["channel"] == "mail"


class TestHierarchy:
    def test_hierarchy_returns_tree_for_parent_user(self, client: TestClient) -> None:
        response = client.get("/api/users/1/hierarchy")
        assert response.status_code == 200
        body = response.json()
        assert "nodes" in body

    def test_hierarchy_for_user_without_children_returns_empty(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/api/users/999/hierarchy")
        assert response.status_code == 200
        body = response.json()
        assert body["nodes"] == []
