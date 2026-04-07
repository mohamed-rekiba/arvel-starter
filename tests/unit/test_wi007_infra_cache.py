"""WI-007 Cache infrastructure tests — MemoryCache and CacheFake.

Covers Epic 004 Story 1: CacheContract usage including put, get, has,
forget, flush, remember, increment, and decrement.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from arvel.cache.drivers.memory_driver import MemoryCache
from arvel.cache.fakes import CacheFake


@pytest.fixture
def cache() -> MemoryCache:
    return MemoryCache()


@pytest.fixture
def cache_fake() -> CacheFake:
    return CacheFake()


class TestMemoryCachePutGet:
    @pytest.mark.anyio
    async def test_put_and_get_returns_value(self, cache: MemoryCache) -> None:
        await cache.put("user:1", "Alice", ttl=60)
        result = await cache.get("user:1")
        assert result == "Alice"

    @pytest.mark.anyio
    async def test_get_missing_key_returns_none(self, cache: MemoryCache) -> None:
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.anyio
    async def test_has_returns_true_for_existing_key(self, cache: MemoryCache) -> None:
        await cache.put("exists", "yes")
        assert await cache.has("exists") is True

    @pytest.mark.anyio
    async def test_has_returns_false_for_missing_key(self, cache: MemoryCache) -> None:
        assert await cache.has("nope") is False


class TestMemoryCacheForgetFlush:
    @pytest.mark.anyio
    async def test_forget_removes_key(self, cache: MemoryCache) -> None:
        await cache.put("key1", "v1")
        await cache.forget("key1")
        assert await cache.get("key1") is None

    @pytest.mark.anyio
    async def test_flush_clears_all_keys(self, cache: MemoryCache) -> None:
        await cache.put("a", 1)
        await cache.put("b", 2)
        await cache.flush()
        assert await cache.has("a") is False
        assert await cache.has("b") is False


class TestMemoryCacheRemember:
    @pytest.mark.anyio
    async def test_remember_computes_on_miss(self, cache: MemoryCache) -> None:
        async def compute() -> str:
            return "computed"

        result = await cache.remember("miss", ttl=60, callback=compute)
        assert result == "computed"

    @pytest.mark.anyio
    async def test_remember_returns_cached_on_hit(self, cache: MemoryCache) -> None:
        await cache.put("hit", "cached-value", ttl=60)

        async def compute() -> str:
            return "should-not-run"

        result = await cache.remember("hit", ttl=60, callback=compute)
        assert result == "cached-value"


class TestMemoryCacheIncrementDecrement:
    @pytest.mark.anyio
    async def test_increment_creates_and_increases(self, cache: MemoryCache) -> None:
        val = await cache.increment("counter")
        assert val == 1
        val = await cache.increment("counter", 5)
        assert val == 6

    @pytest.mark.anyio
    async def test_decrement_reduces_value(self, cache: MemoryCache) -> None:
        await cache.put("counter", 10)
        val = await cache.decrement("counter", 3)
        assert val == 7


class TestCacheFakeAssertions:
    @pytest.mark.anyio
    async def test_assert_put_passes_when_key_set(self, cache_fake: CacheFake) -> None:
        await cache_fake.put("user:1", "Alice")
        cache_fake.assert_put("user:1")

    @pytest.mark.anyio
    async def test_assert_not_put_passes_when_key_absent(
        self, cache_fake: CacheFake
    ) -> None:
        cache_fake.assert_not_put("missing")

    @pytest.mark.anyio
    async def test_assert_nothing_put_passes_when_empty(
        self, cache_fake: CacheFake
    ) -> None:
        cache_fake.assert_nothing_put()


class TestInfraCacheEndpoints:
    @pytest.fixture
    def client(self) -> TestClient:
        import asyncio
        from pathlib import Path

        from arvel.foundation.application import Application

        base_path = Path(__file__).resolve().parents[2]
        app = asyncio.run(Application.create(base_path, testing=True))
        return TestClient(app.asgi_app())

    def test_cache_put_and_get_roundtrip(self, client: TestClient) -> None:
        put_resp = client.post(
            "/api/infra/cache",
            json={"key": "test-key", "value": "hello", "ttl": 120},
        )
        assert put_resp.status_code == 201
        assert put_resp.json()["source"] == "stored"

        get_resp = client.get("/api/infra/cache/test-key")
        assert get_resp.status_code == 200
        body = get_resp.json()
        assert body["value"] == "hello"
        assert body["source"] == "cache"

    def test_cache_get_miss_returns_null(self, client: TestClient) -> None:
        resp = client.get("/api/infra/cache/nonexistent-key")
        assert resp.status_code == 200
        assert resp.json()["source"] == "miss"
        assert resp.json()["value"] is None

    def test_cache_remember_computes_and_caches(self, client: TestClient) -> None:
        resp = client.get("/api/infra/cache/remember-test/remember")
        assert resp.status_code == 200
        body = resp.json()
        assert body["value"] == "computed-value-for-remember-test"
        assert body["source"] == "cache"
