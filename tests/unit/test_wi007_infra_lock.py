"""WI-007 Lock infrastructure tests — MemoryLock and LockFake.

Covers Epic 004 Story 4: LockContract for distributed locking.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from arvel.lock.drivers.memory_driver import MemoryLock
from arvel.lock.fakes import LockFake


@pytest.fixture
def lock() -> MemoryLock:
    return MemoryLock()


@pytest.fixture
def lock_fake() -> LockFake:
    return LockFake()


class TestMemoryLockAcquireRelease:
    @pytest.mark.anyio
    async def test_acquire_succeeds_on_free_key(self, lock: MemoryLock) -> None:
        result = await lock.acquire("job:1", ttl=30)
        assert result is True

    @pytest.mark.anyio
    async def test_acquire_fails_when_already_locked(self, lock: MemoryLock) -> None:
        await lock.acquire("job:1", ttl=30)
        result = await lock.acquire("job:1", ttl=30)
        assert result is False

    @pytest.mark.anyio
    async def test_release_frees_lock(self, lock: MemoryLock) -> None:
        await lock.acquire("job:1", ttl=30)
        await lock.release("job:1")
        result = await lock.acquire("job:1", ttl=30)
        assert result is True

    @pytest.mark.anyio
    async def test_is_locked_reflects_state(self, lock: MemoryLock) -> None:
        assert await lock.is_locked("key") is False
        await lock.acquire("key", ttl=30)
        assert await lock.is_locked("key") is True
        await lock.release("key")
        assert await lock.is_locked("key") is False


class TestMemoryLockWithLock:
    @pytest.mark.anyio
    async def test_with_lock_auto_releases(self, lock: MemoryLock) -> None:
        async with lock.with_lock("auto-key", ttl=30):
            assert await lock.is_locked("auto-key") is True
        assert await lock.is_locked("auto-key") is False


class TestLockFakeAssertions:
    @pytest.mark.anyio
    async def test_assert_acquired_passes_after_acquire(
        self, lock_fake: LockFake
    ) -> None:
        await lock_fake.acquire("test-key", ttl=10)
        lock_fake.assert_acquired("test-key")

    @pytest.mark.anyio
    async def test_assert_nothing_acquired_passes_when_empty(
        self, lock_fake: LockFake
    ) -> None:
        lock_fake.assert_nothing_acquired()


class TestInfraLockEndpoints:
    @pytest.fixture
    def client(self) -> TestClient:
        from pathlib import Path

        from arvel.foundation.application import Application

        base_path = Path(__file__).resolve().parents[2]
        app = asyncio.run(Application.create(base_path, testing=True))
        return TestClient(app.asgi_app())

    def test_lock_acquire_and_check(self, client: TestClient) -> None:
        resp = client.post("/api/infra/lock/resource-1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["acquired"] is True
        assert body["is_locked"] is True

    def test_lock_release(self, client: TestClient) -> None:
        client.post("/api/infra/lock/resource-2")
        resp = client.delete("/api/infra/lock/resource-2")
        assert resp.status_code == 200
        assert resp.json()["is_locked"] is False

    def test_lock_check_unlocked_resource(self, client: TestClient) -> None:
        resp = client.get("/api/infra/lock/never-locked")
        assert resp.status_code == 200
        assert resp.json()["is_locked"] is False
