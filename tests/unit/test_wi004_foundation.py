"""Epic 001 acceptance tests — bootstrap, routes, conftest, packages, Makefile.

These tests verify the structural foundation that makes the starter runnable.
They're written QA-Pre (before implementation) and should initially FAIL.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

STARTER_ROOT = Path(__file__).resolve().parents[2]


class TestBootstrapAppModule:
    """FR-001: bootstrap/app.py exists and exports create_app."""

    def test_bootstrap_app_module_exists(self) -> None:
        app_path = STARTER_ROOT / "bootstrap" / "app.py"
        assert app_path.exists(), "bootstrap/app.py must exist"

    def test_create_app_is_callable(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "bootstrap.app",
            str(STARTER_ROOT / "bootstrap" / "app.py"),
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        factory = getattr(module, "create_app", None)
        assert callable(factory), "bootstrap/app.py must export a callable create_app"

    def test_create_app_returns_application_instance(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "bootstrap.app_test",
            str(STARTER_ROOT / "bootstrap" / "app.py"),
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        app = module.create_app()
        from arvel.foundation.application import Application

        assert isinstance(app, Application), (
            "create_app() must return an Application instance"
        )


class TestRoutesDirectory:
    """FR-002: routes/ directory with api.py exporting a Router."""

    def test_routes_directory_exists(self) -> None:
        routes_dir = STARTER_ROOT / "routes"
        assert routes_dir.is_dir(), "routes/ directory must exist"

    def test_routes_api_module_exists(self) -> None:
        api_path = STARTER_ROOT / "routes" / "api.py"
        assert api_path.exists(), "routes/api.py must exist"

    def test_routes_api_exports_router(self) -> None:
        from arvel.http.router import Router

        spec = importlib.util.spec_from_file_location(
            "routes.api",
            str(STARTER_ROOT / "routes" / "api.py"),
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules["routes.api"] = module
        spec.loader.exec_module(module)
        router = getattr(module, "router", None)
        assert isinstance(router, Router), (
            "routes/api.py must export 'router' as a Router instance"
        )


class TestRouteDiscovery:
    """FR-002b: Framework discovers routes and mounts them on /api/*."""

    def test_api_users_route_is_discoverable(self, client: TestClient) -> None:
        response = client.get("/api/users")
        assert response.status_code == 200, (
            "GET /api/users must be reachable after route discovery"
        )

    def test_api_users_store_route_is_discoverable(self, client: TestClient) -> None:
        import uuid

        response = client.post(
            "/api/users",
            json={
                "name": "Test",
                "email": f"route-{uuid.uuid7().hex[:8]}@test.com",
                "password": "securepass",
            },
        )
        assert response.status_code == 201

    def test_api_users_show_route_is_discoverable(self, client: TestClient) -> None:
        response = client.get("/api/users/id/1")
        assert response.status_code == 200


class TestConftest:
    """FR-003: tests/conftest.py provides shared fixtures."""

    def test_conftest_exists(self) -> None:
        conftest_path = STARTER_ROOT / "tests" / "conftest.py"
        assert conftest_path.exists(), "tests/conftest.py must exist"

    def test_client_fixture_works(self, client: TestClient) -> None:
        assert client is not None, "client fixture must be provided by conftest.py"

    def test_client_fixture_can_reach_api(self, client: TestClient) -> None:
        response = client.get("/api/users")
        assert response.status_code != 404, (
            "client fixture must be wired to a booted app with routes"
        )


class TestPackageInit:
    """FR-004: __init__.py files in all application packages."""

    @pytest.mark.parametrize(
        "package_path",
        [
            pytest.param("app", id="app"),
            pytest.param("app/models", id="app-models"),
            pytest.param("app/http", id="app-http"),
            pytest.param("app/http/controllers", id="app-http-controllers"),
            pytest.param("app/http/resources", id="app-http-resources"),
            pytest.param("bootstrap", id="bootstrap"),
            pytest.param("config", id="config"),
            pytest.param("database", id="database"),
            pytest.param("database/factories", id="database-factories"),
            pytest.param("database/seeders", id="database-seeders"),
            pytest.param("database/migrations", id="database-migrations"),
            pytest.param("routes", id="routes"),
        ],
    )
    def test_init_file_exists(self, package_path: str) -> None:
        init_path = STARTER_ROOT / package_path / "__init__.py"
        assert init_path.exists(), f"{package_path}/__init__.py must exist"


class TestMakefile:
    """FR-005: Makefile with standard targets."""

    def test_makefile_exists(self) -> None:
        makefile_path = STARTER_ROOT / "Makefile"
        assert makefile_path.exists(), "Makefile must exist in the starter root"

    @pytest.mark.parametrize(
        "target",
        [
            pytest.param("sync", id="sync"),
            pytest.param("run", id="run"),
            pytest.param("test", id="test"),
            pytest.param("lint", id="lint"),
            pytest.param("check", id="check"),
        ],
    )
    def test_makefile_has_target(self, target: str) -> None:
        makefile_path = STARTER_ROOT / "Makefile"
        content = makefile_path.read_text()
        assert f"{target}:" in content, f"Makefile must define '{target}' target"
