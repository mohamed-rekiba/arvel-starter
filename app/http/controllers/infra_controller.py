"""Infrastructure demo controller — showcases Cache, Lock, and Storage contracts.

Dependencies are declared in method signatures via ``Inject()`` and
resolved from the Arvel DI container at request time.
"""

from __future__ import annotations

import base64
import binascii
import logging
from typing import Any

from arvel.cache.contracts import CacheContract
from arvel.http import BaseController, HTTPException, Inject, route, status
from arvel.lock.contracts import LockContract
from arvel.storage.contracts import StorageContract
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CacheDemoResponse(BaseModel):
    key: str
    value: Any = None
    source: str = ""


class CachePutRequest(BaseModel):
    key: str = Field(min_length=1, max_length=255)
    value: str = Field(min_length=1)
    ttl: int | None = None


class LockDemoResponse(BaseModel):
    key: str
    acquired: bool
    is_locked: bool


class StorageDemoResponse(BaseModel):
    path: str
    action: str
    url: str | None = None
    size: int | None = None
    exists: bool | None = None


class StoragePutRequest(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content_base64: str = Field(min_length=1)
    content_type: str | None = None


class InfraController(BaseController):
    description = "Infrastructure service demonstrations (cache, lock, storage)."
    tags = ("infrastructure",)
    prefix = "/infra"

    # --- Cache endpoints ---

    @route.get(
        "/cache/{key}",
        response_model=CacheDemoResponse,
        summary="Get a cached value",
        operation_id="infra_cache_get",
    )
    async def cache_get(
        self,
        key: str,
        cache: CacheContract = Inject(CacheContract),
    ) -> CacheDemoResponse:
        value = await cache.get(key)
        source = "cache" if value is not None else "miss"
        return CacheDemoResponse(key=key, value=value, source=source)

    @route.post(
        "/cache",
        response_model=CacheDemoResponse,
        status_code=201,
        summary="Put a value in cache",
        operation_id="infra_cache_put",
    )
    async def cache_put(
        self,
        payload: CachePutRequest,
        cache: CacheContract = Inject(CacheContract),
    ) -> CacheDemoResponse:
        await cache.put(payload.key, payload.value, ttl=payload.ttl)
        return CacheDemoResponse(key=payload.key, value=payload.value, source="stored")

    @route.get(
        "/cache/{key}/remember",
        response_model=CacheDemoResponse,
        summary="Demonstrate cache.remember() pattern",
        operation_id="infra_cache_remember",
    )
    async def cache_remember(
        self,
        key: str,
        cache: CacheContract = Inject(CacheContract),
    ) -> CacheDemoResponse:
        async def _compute() -> str:
            return f"computed-value-for-{key}"

        value = await cache.remember(key, ttl=60, callback=_compute)
        cached = await cache.has(key)
        source = "cache" if cached else "computed"
        return CacheDemoResponse(key=key, value=value, source=source)

    # --- Lock endpoints ---

    @route.post(
        "/lock/{key}",
        response_model=LockDemoResponse,
        summary="Acquire a lock",
        operation_id="infra_lock_acquire",
    )
    async def lock_acquire(
        self,
        key: str,
        lock: LockContract = Inject(LockContract),
    ) -> LockDemoResponse:
        acquired = await lock.acquire(key, ttl=30)
        is_locked = await lock.is_locked(key)
        return LockDemoResponse(key=key, acquired=acquired, is_locked=is_locked)

    @route.delete(
        "/lock/{key}",
        response_model=LockDemoResponse,
        summary="Release a lock",
        operation_id="infra_lock_release",
    )
    async def lock_release(
        self,
        key: str,
        lock: LockContract = Inject(LockContract),
    ) -> LockDemoResponse:
        await lock.release(key)
        is_locked = await lock.is_locked(key)
        return LockDemoResponse(key=key, acquired=False, is_locked=is_locked)

    @route.get(
        "/lock/{key}",
        response_model=LockDemoResponse,
        summary="Check if a resource is locked",
        operation_id="infra_lock_check",
    )
    async def lock_check(
        self,
        key: str,
        lock: LockContract = Inject(LockContract),
    ) -> LockDemoResponse:
        is_locked = await lock.is_locked(key)
        return LockDemoResponse(key=key, acquired=False, is_locked=is_locked)

    # --- Storage endpoints ---

    @route.post(
        "/storage",
        response_model=StorageDemoResponse,
        status_code=201,
        summary="Store a file",
        operation_id="infra_storage_put",
    )
    async def storage_put(
        self,
        payload: StoragePutRequest,
        storage: StorageContract = Inject(StorageContract),
    ) -> StorageDemoResponse:
        try:
            data = base64.b64decode(payload.content_base64)
        except ValueError, binascii.Error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 content",
            )
        await storage.put(payload.path, data, content_type=payload.content_type)
        url = await storage.url(payload.path)
        return StorageDemoResponse(
            path=payload.path, action="stored", url=url, size=len(data)
        )

    @route.get(
        "/storage/{path:path}",
        response_model=StorageDemoResponse,
        summary="Check if a file exists and get its URL",
        operation_id="infra_storage_info",
    )
    async def storage_info(
        self,
        path: str,
        storage: StorageContract = Inject(StorageContract),
    ) -> StorageDemoResponse:
        exists = await storage.exists(path)
        url = await storage.url(path) if exists else None
        size = await storage.size(path) if exists else None
        return StorageDemoResponse(
            path=path, action="info", url=url, size=size, exists=exists
        )

    @route.delete(
        "/storage/{path:path}",
        response_model=StorageDemoResponse,
        summary="Delete a file from storage",
        operation_id="infra_storage_delete",
    )
    async def storage_delete(
        self,
        path: str,
        storage: StorageContract = Inject(StorageContract),
    ) -> StorageDemoResponse:
        deleted = await storage.delete(path)
        return StorageDemoResponse(
            path=path, action="deleted" if deleted else "not_found", exists=not deleted
        )
