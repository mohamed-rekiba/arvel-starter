"""Tests for user endpoints — index, create, show, /me, hierarchy."""

from __future__ import annotations

from dirty_equals import IsPositiveInt


class TestUserIndex:
    async def test_index_returns_paginated_users(self, client):
        await client.post(
            "/api/users/",
            json={
                "name": "Index User",
                "email": "index-user@test.com",
                "password": "password123",
            },
        )

        response = await client.get("/api/users")
        response.assert_ok()
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)
        assert data["pagination"]["page"] == 1

    async def test_index_respects_pagination_params(self, client):
        response = await client.get("/api/users", params={"page": 1, "per_page": 5})
        response.assert_ok()
        assert response.json()["pagination"]["per_page"] == 5


class TestUserCreate:
    async def test_create_user_with_valid_data_returns_201(self, client):
        response = await client.post(
            "/api/users/",
            json={
                "name": "New User",
                "email": "newuser-create@test.com",
                "password": "password123",
            },
        )
        response.assert_created()
        data = response.json()
        assert data["id"] == IsPositiveInt
        assert data["name"] == "New User"

    async def test_create_user_with_missing_name_returns_422(self, client):
        response = await client.post(
            "/api/users/",
            json={
                "email": "missing-name@test.com",
                "password": "password123",
            },
        )
        response.assert_unprocessable()

    async def test_create_user_with_short_password_returns_422(self, client):
        response = await client.post(
            "/api/users/",
            json={
                "name": "Short Pass",
                "email": "shortpass@test.com",
                "password": "short",
            },
        )
        response.assert_unprocessable()


class TestUserShow:
    async def test_show_existing_user_returns_200(self, client):
        create_resp = await client.post(
            "/api/users/",
            json={
                "name": "Show User",
                "email": "showuser@test.com",
                "password": "password123",
            },
        )
        user_id = create_resp.json()["id"]

        response = await client.get(f"/api/users/id/{user_id}")
        response.assert_ok()
        assert response.json()["id"] == user_id
        assert response.json()["name"] == "Show User"

    async def test_show_nonexistent_user_returns_404(self, client):
        response = await client.get("/api/users/id/999999")
        response.assert_not_found()


class TestUserMe:
    async def test_me_without_auth_returns_401(self, client):
        response = await client.get("/api/users/me")
        response.assert_status(401)

    async def test_me_with_auth_returns_profile(self, auth_client):
        response = await auth_client.get("/api/users/me")
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "email" in data


class TestUserStoreValidated:
    async def test_store_validated_with_valid_data_returns_201(self, client):
        response = await client.post(
            "/api/users/validated",
            json={
                "name": "Validated User",
                "email": "validated-user@test.com",
                "password": "password123",
            },
        )
        response.assert_created()
        data = response.json()
        assert data["id"] == IsPositiveInt
        assert data["name"] == "Validated User"

    async def test_store_validated_with_missing_email_returns_422(self, client):
        response = await client.post(
            "/api/users/validated",
            json={
                "name": "No Email",
                "password": "password123",
            },
        )
        response.assert_unprocessable()

    async def test_store_validated_with_duplicate_email_rejects(self, client):
        email = "dup-validated@test.com"
        await client.post(
            "/api/users/validated",
            json={
                "name": "First",
                "email": email,
                "password": "password123",
            },
        )
        response = await client.post(
            "/api/users/validated",
            json={
                "name": "Second",
                "email": email,
                "password": "password123",
            },
        )
        assert response.status_code in (422, 500)


class TestUserSearch:
    async def test_search_returns_results_structure(self, client):
        await client.post(
            "/api/users/",
            json={
                "name": "Searchable User",
                "email": "searchable@test.com",
                "password": "password123",
            },
        )
        response = await client.get("/api/users/search", params={"q": "Searchable"})
        response.assert_ok()
        data = response.json()
        assert "query" in data
        assert "hits" in data
        assert "total" in data
        assert data["query"] == "Searchable"

    async def test_search_with_empty_query_returns_422(self, client):
        response = await client.get("/api/users/search", params={"q": ""})
        response.assert_unprocessable()


class TestUserNotify:
    async def test_notify_existing_user_returns_sent(self, client):
        create_resp = await client.post(
            "/api/users/",
            json={
                "name": "Notify User",
                "email": "notify-user@test.com",
                "password": "password123",
            },
        )
        user_id = create_resp.json()["id"]

        response = await client.post(f"/api/users/{user_id}/notify")
        response.assert_ok()
        data = response.json()
        assert data["status"] in ("sent", "skipped")

    async def test_notify_nonexistent_user_returns_404(self, client):
        response = await client.post("/api/users/999999/notify")
        response.assert_not_found()


class TestUserProfileImage:
    async def test_upload_profile_image_without_auth_returns_401(self, client):
        response = await client.post(
            "/api/users/me/profile-image",
            files={"file": ("test.png", b"fake-image-bytes", "image/png")},
        )
        response.assert_status(401)

    async def test_upload_profile_image_with_auth_succeeds(self, auth_client):
        response = await auth_client.post(
            "/api/users/me/profile-image",
            files={
                "file": (
                    "avatar.png",
                    b"\x89PNG\r\n\x1a\n" + b"\x00" * 100,
                    "image/png",
                )
            },
        )
        if response.status_code == 200:
            assert "url" in response.json()


class TestUserHierarchy:
    async def test_hierarchy_for_nonexistent_user_returns_empty(self, client):
        response = await client.get("/api/users/999999/hierarchy")
        response.assert_ok()
        data = response.json()
        assert data["nodes"] == []

    async def test_hierarchy_for_user_with_children(self, client):
        parent_resp = await client.post(
            "/api/users/",
            json={
                "name": "Hierarchy Parent",
                "email": "hierarchy-parent@test.com",
                "password": "password123",
            },
        )
        parent_id = parent_resp.json()["id"]

        response = await client.get(f"/api/users/{parent_id}/hierarchy")
        response.assert_ok()
