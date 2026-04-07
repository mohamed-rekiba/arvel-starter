"""WI-010 Search tests — CollectionEngine, Searchable mixin, search endpoint.

Covers Epic 007 Stories 1-2: full-text search via CollectionEngine
with the Searchable mixin on User, and the /api/users/search endpoint.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from arvel.search import SearchManager, SearchSettings
from arvel.search.drivers.collection_driver import CollectionEngine

from app.models.user import User


class TestCollectionEngineUpsertSearch:
    @pytest.mark.anyio
    async def test_upsert_and_search_finds_document(self) -> None:
        engine = CollectionEngine()
        await engine.create_index("users")
        await engine.upsert_documents(
            "users",
            [{"id": 1, "name": "Alice", "email": "alice@test.com"}],
        )
        result = await engine.search("users", "alice")
        assert result.total == 1
        assert result.hits[0].id == 1
        assert result.hits[0].score > 0

    @pytest.mark.anyio
    async def test_search_returns_empty_on_no_match(self) -> None:
        engine = CollectionEngine()
        await engine.create_index("users")
        await engine.upsert_documents(
            "users",
            [{"id": 1, "name": "Alice", "email": "alice@test.com"}],
        )
        result = await engine.search("users", "zzzznotfound")
        assert result.total == 0
        assert result.hits == []

    @pytest.mark.anyio
    async def test_upsert_updates_existing_document(self) -> None:
        engine = CollectionEngine()
        await engine.create_index("users")
        await engine.upsert_documents("users", [{"id": 1, "name": "Alice"}])
        await engine.upsert_documents("users", [{"id": 1, "name": "Alice Updated"}])
        result = await engine.search("users", "Updated")
        assert result.total == 1
        assert result.hits[0].id == 1

    @pytest.mark.anyio
    async def test_empty_query_returns_all_documents(self) -> None:
        engine = CollectionEngine()
        await engine.create_index("users")
        await engine.upsert_documents(
            "users",
            [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
                {"id": 3, "name": "Charlie"},
            ],
        )
        result = await engine.search("users", "")
        assert result.total == 3


class TestCollectionEngineRemoveFlush:
    @pytest.mark.anyio
    async def test_remove_deletes_document(self) -> None:
        engine = CollectionEngine()
        await engine.create_index("users")
        await engine.upsert_documents("users", [{"id": 1, "name": "Alice"}])
        await engine.remove_documents("users", [1])
        result = await engine.search("users", "Alice")
        assert result.total == 0

    @pytest.mark.anyio
    async def test_flush_clears_all_documents(self) -> None:
        engine = CollectionEngine()
        await engine.create_index("users")
        await engine.upsert_documents(
            "users",
            [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
        )
        await engine.flush("users")
        result = await engine.search("users", "")
        assert result.total == 0


class TestCollectionEngineIndexLifecycle:
    @pytest.mark.anyio
    async def test_create_index_is_idempotent(self) -> None:
        engine = CollectionEngine()
        await engine.create_index("test")
        await engine.create_index("test")
        await engine.upsert_documents("test", [{"id": 1, "name": "ok"}])
        result = await engine.search("test", "ok")
        assert result.total == 1

    @pytest.mark.anyio
    async def test_delete_index_removes_all_data(self) -> None:
        engine = CollectionEngine()
        await engine.create_index("test")
        await engine.upsert_documents("test", [{"id": 1, "name": "data"}])
        await engine.delete_index("test")
        from arvel.search.exceptions import SearchIndexNotFoundError

        with pytest.raises(SearchIndexNotFoundError):
            await engine.search("test", "data")

    @pytest.mark.anyio
    async def test_delete_nonexistent_index_is_silent(self) -> None:
        engine = CollectionEngine()
        await engine.delete_index("nonexistent")


class TestCollectionEngineFilters:
    @pytest.mark.anyio
    async def test_filter_narrows_results(self) -> None:
        engine = CollectionEngine()
        await engine.create_index("users")
        await engine.upsert_documents(
            "users",
            [
                {"id": 1, "name": "Alice", "role": "admin"},
                {"id": 2, "name": "Bob", "role": "user"},
            ],
        )
        result = await engine.search("users", "", filters={"role": "admin"})
        assert result.total == 1
        assert result.hits[0].id == 1


class TestCollectionEnginePagination:
    @pytest.mark.anyio
    async def test_limit_and_offset(self) -> None:
        engine = CollectionEngine()
        await engine.create_index("items")
        docs = [{"id": i, "name": f"Item {i}"} for i in range(10)]
        await engine.upsert_documents("items", docs)

        page1 = await engine.search("items", "", limit=3, offset=0)
        assert len(page1.hits) == 3
        assert page1.total == 10

        page2 = await engine.search("items", "", limit=3, offset=3)
        assert len(page2.hits) == 3
        page1_ids = {h.id for h in page1.hits}
        page2_ids = {h.id for h in page2.hits}
        assert page1_ids.isdisjoint(page2_ids)


class TestSearchManagerDriverResolution:
    def test_collection_driver_resolved_for_collection_setting(self) -> None:
        settings = SearchSettings(driver="collection")
        engine = SearchManager().create_driver(settings)
        assert isinstance(engine, CollectionEngine)

    def test_null_driver_resolved_for_null_setting(self) -> None:
        from arvel.search.drivers.null_driver import NullEngine

        settings = SearchSettings(driver="null")
        engine = SearchManager().create_driver(settings)
        assert isinstance(engine, NullEngine)

    def test_unknown_driver_rejected_by_settings_validation(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="literal_error"):
            SearchSettings.model_validate({"driver": "bogus"})


class TestSearchableMixinOnUser:
    def test_user_has_searchable_fields(self) -> None:
        assert "name" in User.__searchable__
        assert "email" in User.__searchable__
        assert "password" not in User.__searchable__

    def test_search_index_name_uses_tablename(self) -> None:
        assert User.search_index_name() == "users"


class TestSearchEndpoint:
    @pytest.fixture
    def client(self) -> TestClient:
        from arvel.foundation.application import Application

        base_path = Path(__file__).resolve().parents[2]
        app = asyncio.run(Application.create(base_path, testing=True))
        return TestClient(app.asgi_app())

    def test_search_with_empty_query_returns_422(self, client: TestClient) -> None:
        resp = client.get("/api/users/search")
        assert resp.status_code == 422

    def test_search_with_query_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/users/search?q=alice")
        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "alice"
        assert isinstance(body["hits"], list)
        assert isinstance(body["total"], int)

    def test_search_result_does_not_expose_password(self, client: TestClient) -> None:
        resp = client.get("/api/users/search?q=bob")
        assert resp.status_code == 200
        for hit in resp.json().get("hits", []):
            assert "password" not in hit

    def test_search_no_match_returns_empty_list(self, client: TestClient) -> None:
        resp = client.get("/api/users/search?q=zzzznonexistent999")
        assert resp.status_code == 200
        body = resp.json()
        assert body["hits"] == []
        assert body["total"] == 0
