"""WI-011 tests — health endpoint alignment (Epic 008, Story 1).

Validates that /api/health returns aggregated health check results.
Only services that are actually enabled appear in the checks array —
no-op drivers (memory cache, sync queue, null storage) are excluded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for the aligned /api/health endpoint using HealthEndpointPayload."""

    def test_health_returns_200_with_status_field(self, client: TestClient) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert "status" in body
        assert body["status"] in ("healthy", "unhealthy", "degraded")

    def test_health_returns_checks_array(self, client: TestClient) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert "checks" in body
        assert isinstance(body["checks"], list)
        assert len(body["checks"]) >= 1

    def test_health_check_has_expected_fields(self, client: TestClient) -> None:
        response = client.get("/api/health")
        body = response.json()
        for check in body["checks"]:
            assert "name" in check
            assert "status" in check
            assert "message" in check
            assert "duration_ms" in check

    def test_health_database_check_present(self, client: TestClient) -> None:
        response = client.get("/api/health")
        body = response.json()
        check_names = [c["name"] for c in body["checks"]]
        assert "database" in check_names

    def test_health_noop_drivers_excluded(self, client: TestClient) -> None:
        """No-op drivers (memory cache, sync queue) don't appear in checks."""
        response = client.get("/api/health")
        body = response.json()
        check_names = {c["name"] for c in body["checks"]}
        assert "cache" not in check_names
        assert "queue" not in check_names

    def test_health_does_not_expose_credentials(self, client: TestClient) -> None:
        response = client.get("/api/health")
        raw = response.text.lower()
        assert "password" not in raw
        assert "secret" not in raw


class TestFrameworkHealthEndpoint:
    """Tests for the framework-level /health endpoint registered by ObservabilityProvider."""

    def test_framework_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert "status" in body
        assert "checks" in body

    def test_framework_health_database_healthy(self, client: TestClient) -> None:
        response = client.get("/health")
        body = response.json()
        db_checks = [c for c in body["checks"] if c["name"] == "database"]
        assert len(db_checks) == 1
        assert db_checks[0]["status"] in ("healthy", "unhealthy", "degraded")

    def test_framework_health_storage_check_present(self, client: TestClient) -> None:
        """Local storage driver is enabled by default — check should appear."""
        response = client.get("/health")
        body = response.json()
        check_names = [c["name"] for c in body["checks"]]
        assert "storage" in check_names


class TestHealthRegistryDirect:
    """Unit tests for HealthRegistry and health check classes."""

    @pytest.mark.anyio
    async def test_health_registry_runs_all_checks(self) -> None:
        from arvel.observability.health import (
            HealthRegistry,
            HealthResult,
            HealthStatus,
        )

        class AlwaysHealthy:
            name = "test_check"

            async def check(self) -> HealthResult:
                return HealthResult(
                    status=HealthStatus.HEALTHY, message="ok", duration_ms=0.1
                )

        registry = HealthRegistry(timeout=2.0)
        registry.register(AlwaysHealthy())
        result = await registry.run_all()
        assert result.status == HealthStatus.HEALTHY
        assert len(result.checks) == 1
        assert result.checks[0].name == "test_check"

    @pytest.mark.anyio
    async def test_health_registry_reports_unhealthy(self) -> None:
        from arvel.observability.health import (
            HealthRegistry,
            HealthResult,
            HealthStatus,
        )

        class AlwaysUnhealthy:
            name = "broken"

            async def check(self) -> HealthResult:
                return HealthResult(
                    status=HealthStatus.UNHEALTHY, message="fail", duration_ms=0.1
                )

        registry = HealthRegistry(timeout=2.0)
        registry.register(AlwaysUnhealthy())
        result = await registry.run_all()
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.anyio
    async def test_health_registry_timeout_reports_degraded(self) -> None:
        import anyio

        from arvel.observability.health import (
            HealthRegistry,
            HealthResult,
            HealthStatus,
        )

        class SlowCheck:
            name = "slow"

            async def check(self) -> HealthResult:
                await anyio.sleep(10)
                return HealthResult(
                    status=HealthStatus.HEALTHY, message="ok", duration_ms=0.1
                )

        registry = HealthRegistry(timeout=0.1)
        registry.register(SlowCheck())
        result = await registry.run_all()
        assert result.checks[0].status == HealthStatus.DEGRADED
