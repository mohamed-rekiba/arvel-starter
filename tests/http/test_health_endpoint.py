"""Tests for the health endpoint."""

from __future__ import annotations


class TestHealthCheck:
    async def test_health_returns_200_with_status(self, client):
        response = await client.get("/api/health/")
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data

    async def test_health_includes_checks(self, client):
        response = await client.get("/api/health/")
        data = response.json()
        assert "checks" in data
        assert isinstance(data["checks"], list)
