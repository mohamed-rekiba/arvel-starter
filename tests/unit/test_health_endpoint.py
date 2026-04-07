"""Health controller endpoint tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_health_endpoint_returns_status_field(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert body["status"] in ("healthy", "unhealthy", "degraded")


def test_health_endpoint_content_type_is_json(client: TestClient) -> None:
    response = client.get("/api/health")
    assert "application/json" in response.headers["content-type"]
