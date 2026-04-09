"""Tests for infrastructure endpoints — cache, lock, storage."""

from __future__ import annotations

import base64


class TestCacheEndpoints:
    async def test_cache_get_miss_returns_null_value(self, client):
        response = await client.get("/api/infra/cache/test-miss-key")
        response.assert_ok()
        data = response.json()
        assert data["key"] == "test-miss-key"
        assert data["source"] == "miss"

    async def test_cache_put_stores_value(self, client):
        response = await client.post(
            "/api/infra/cache",
            json={
                "key": "test-put-key",
                "value": "hello",
            },
        )
        response.assert_created()
        assert response.json()["source"] == "stored"

    async def test_cache_put_then_get_returns_value(self, client):
        await client.post(
            "/api/infra/cache",
            json={
                "key": "test-roundtrip",
                "value": "world",
            },
        )
        response = await client.get("/api/infra/cache/test-roundtrip")
        response.assert_ok()
        assert response.json()["value"] == "world"
        assert response.json()["source"] == "cache"

    async def test_cache_remember_computes_and_caches(self, client):
        response = await client.get("/api/infra/cache/test-remember-key/remember")
        response.assert_ok()
        data = response.json()
        assert data["value"] == "computed-value-for-test-remember-key"


class TestLockEndpoints:
    async def test_lock_acquire_returns_acquired(self, client):
        response = await client.post("/api/infra/lock/test-lock-key")
        response.assert_ok()
        data = response.json()
        assert data["acquired"] is True
        assert data["is_locked"] is True

        await client.delete("/api/infra/lock/test-lock-key")

    async def test_lock_release_clears_lock(self, client):
        await client.post("/api/infra/lock/test-release-key")

        response = await client.delete("/api/infra/lock/test-release-key")
        response.assert_ok()
        assert response.json()["is_locked"] is False

    async def test_lock_check_reflects_state(self, client):
        response = await client.get("/api/infra/lock/unacquired-key")
        response.assert_ok()
        assert response.json()["is_locked"] is False


class TestStorageEndpoints:
    async def test_storage_put_stores_file(self, client):
        content = base64.b64encode(b"hello storage").decode()
        response = await client.post(
            "/api/infra/storage",
            json={
                "path": "test/hello.txt",
                "content_base64": content,
                "content_type": "text/plain",
            },
        )
        response.assert_created()
        data = response.json()
        assert data["action"] == "stored"
        assert data["size"] == len(b"hello storage")

    async def test_storage_info_for_existing_file(self, client):
        content = base64.b64encode(b"info test").decode()
        await client.post(
            "/api/infra/storage",
            json={
                "path": "test/info.txt",
                "content_base64": content,
            },
        )

        response = await client.get("/api/infra/storage/test/info.txt")
        response.assert_ok()
        assert response.json()["exists"] is True

    async def test_storage_info_for_missing_file(self, client):
        response = await client.get("/api/infra/storage/nonexistent/file.txt")
        response.assert_ok()
        assert response.json()["exists"] is False

    async def test_storage_delete_removes_file(self, client):
        content = base64.b64encode(b"delete me").decode()
        await client.post(
            "/api/infra/storage",
            json={
                "path": "test/delete.txt",
                "content_base64": content,
            },
        )

        response = await client.delete("/api/infra/storage/test/delete.txt")
        response.assert_ok()
        assert response.json()["action"] == "deleted"
