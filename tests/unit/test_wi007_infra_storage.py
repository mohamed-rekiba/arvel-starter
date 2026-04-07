"""WI-007 Storage infrastructure tests — LocalStorage and StorageFake.

Covers Epic 004 Story 3: StorageContract for file operations.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from arvel.storage.drivers.local_driver import LocalStorage
from arvel.storage.fakes import StorageFake


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(root=str(tmp_path), base_url="http://localhost:8000/files")


@pytest.fixture
def storage_fake() -> StorageFake:
    return StorageFake()


class TestLocalStoragePutGetDelete:
    @pytest.mark.anyio
    async def test_put_and_get_roundtrip(self, storage: LocalStorage) -> None:
        content = b"hello world"
        await storage.put("test.txt", content)
        result = await storage.get("test.txt")
        assert result == content

    @pytest.mark.anyio
    async def test_exists_returns_true_after_put(self, storage: LocalStorage) -> None:
        await storage.put("file.bin", b"data")
        assert await storage.exists("file.bin") is True

    @pytest.mark.anyio
    async def test_exists_returns_false_for_missing(
        self, storage: LocalStorage
    ) -> None:
        assert await storage.exists("missing.txt") is False

    @pytest.mark.anyio
    async def test_delete_removes_file(self, storage: LocalStorage) -> None:
        await storage.put("to-delete.txt", b"data")
        result = await storage.delete("to-delete.txt")
        assert result is True
        assert await storage.exists("to-delete.txt") is False

    @pytest.mark.anyio
    async def test_size_returns_byte_count(self, storage: LocalStorage) -> None:
        data = b"12345"
        await storage.put("sized.txt", data)
        size = await storage.size("sized.txt")
        assert size == 5

    @pytest.mark.anyio
    async def test_url_returns_public_path(self, storage: LocalStorage) -> None:
        await storage.put("public.txt", b"ok")
        url = await storage.url("public.txt")
        assert url.startswith("http://localhost:8000/files")
        assert "public.txt" in url


class TestLocalStorageList:
    @pytest.mark.anyio
    async def test_list_returns_stored_files(self, storage: LocalStorage) -> None:
        await storage.put("dir/a.txt", b"a")
        await storage.put("dir/b.txt", b"b")
        files = await storage.list("dir")
        assert "dir/a.txt" in files
        assert "dir/b.txt" in files


class TestStorageFakeAssertions:
    @pytest.mark.anyio
    async def test_assert_stored_passes_after_put(
        self, storage_fake: StorageFake
    ) -> None:
        await storage_fake.put("file.txt", b"data")
        storage_fake.assert_stored("file.txt")

    @pytest.mark.anyio
    async def test_assert_not_stored_passes_when_absent(
        self, storage_fake: StorageFake
    ) -> None:
        storage_fake.assert_not_stored("missing.txt")

    @pytest.mark.anyio
    async def test_assert_nothing_stored_passes_when_empty(
        self, storage_fake: StorageFake
    ) -> None:
        storage_fake.assert_nothing_stored()
