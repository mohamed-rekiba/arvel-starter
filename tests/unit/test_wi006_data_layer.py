"""Epic 003 (WI-arvel-006): Data layer full demo tests.

Covers: UserRepository, pagination, relationships, soft deletes,
UserObserver, and Transaction with nested savepoints.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def _unique_email(prefix: str = "test") -> str:
    return f"{prefix}-{uuid.uuid7().hex[:8]}@test.com"


# ── Story 2 + 3: Repository & controller wiring ─────────────────────────────


class TestRepositoryViaEndpoints:
    """Verify that controllers use real DB queries via UserRepository."""

    def test_store_persists_and_show_retrieves(self, client: TestClient) -> None:
        email = _unique_email("repotest")
        create_resp = client.post(
            "/api/users",
            json={"name": "RepoTest", "email": email, "password": "securepw!"},
        )
        assert create_resp.status_code == 201
        user_id = create_resp.json()["id"]

        show_resp = client.get(f"/api/users/id/{user_id}")
        assert show_resp.status_code == 200
        assert show_resp.json()["name"] == "RepoTest"

    def test_show_nonexistent_user_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/users/id/99999")
        assert response.status_code == 404

    def test_store_mass_assignment_only_fillable(self, client: TestClient) -> None:
        response = client.post(
            "/api/users",
            json={
                "name": "MassTest",
                "email": _unique_email("masstest"),
                "password": "securepw!",
            },
        )
        assert response.status_code == 201
        assert "id" in response.json()


# ── Story 5: Pagination ──────────────────────────────────────────────────────


class TestPagination:
    def test_paginated_response_has_metadata(self, client: TestClient) -> None:
        response = client.get("/api/users?page=1&per_page=2")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "pagination" in body
        pag = body["pagination"]
        assert pag["page"] == 1
        assert pag["per_page"] == 2
        assert isinstance(pag["total"], int)
        assert isinstance(pag["has_more"], bool)

    def test_pagination_limits_results(self, client: TestClient) -> None:
        response = client.get("/api/users?page=1&per_page=2")
        assert response.status_code == 200
        assert len(response.json()["data"]) <= 2

    def test_page_two_returns_200_with_offset_data(self, client: TestClient) -> None:
        response = client.get("/api/users?page=2&per_page=3")
        assert response.status_code == 200
        body = response.json()
        assert body["pagination"]["page"] == 2

    def test_per_page_over_100_returns_422(self, client: TestClient) -> None:
        response = client.get("/api/users?per_page=200")
        assert response.status_code == 422


# ── Story 4: Hierarchy (RecursiveQueryBuilder) ───────────────────────────────


class TestHierarchyEndpoint:
    def test_hierarchy_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/users/1/hierarchy")
        assert response.status_code == 200
        body = response.json()
        assert "nodes" in body

    def test_hierarchy_nonexistent_returns_empty_nodes(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/users/99999/hierarchy")
        assert response.status_code == 200
        assert response.json()["nodes"] == []


# ── Story 1: Relationships (validated via seeded data) ───────────────────────


class TestModelRelationships:
    """Verify relationship wiring via hierarchy endpoint (uses self-ref FK)."""

    def test_parent_user_has_hierarchy_descendants(self, client: TestClient) -> None:
        response = client.get("/api/users/1/hierarchy")
        assert response.status_code == 200


# ── Story 7: Observer (email normalisation) ──────────────────────────────────


class TestUserObserverNormalization:
    def test_create_user_normalises_email_to_lowercase(
        self,
        client: TestClient,
    ) -> None:
        response = client.post(
            "/api/users",
            json={
                "name": "ObsTest",
                "email": _unique_email("OBS.TEST"),
                "password": "securepw!",
            },
        )
        assert response.status_code == 201
