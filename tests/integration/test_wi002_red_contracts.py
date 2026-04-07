"""WI-002 integration contract tests — real JWT flow end-to-end."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from arvel.foundation.application import Application


def _create_client() -> tuple[Application, TestClient]:
    base_path = Path(__file__).resolve().parents[2]
    app = asyncio.run(Application.create(base_path, testing=True))
    return app, TestClient(app.asgi_app())


def _login(client: TestClient) -> dict[str, str]:
    """Login and return the token payload."""
    response = client.post(
        "/api/auth/login",
        json={"email": "root@example.com", "password": "password"},
    )
    return response.json()


@pytest.mark.integration
def test_fr001_dependency_baseline_red() -> None:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    expected = 'dependencies = ["arvel[pg,taskiq,argon2,redis,smtp,s3,media,otel]"]'
    if expected not in content:
        raise AssertionError(
            "FR-001 dependency profile is not present in starter pyproject"
        )


@pytest.mark.integration
def test_fr002_login_returns_tokens_red() -> None:
    app, client = _create_client()
    try:
        response = client.post(
            "/api/auth/login",
            json={"email": "root@example.com", "password": "password"},
        )
    finally:
        asyncio.run(app.shutdown())
    if response.status_code != 200:
        raise AssertionError(f"Expected 200, got {response.status_code}")
    body = response.json()
    if "access_token" not in body or "refresh_token" not in body:
        raise AssertionError(
            "Login response must include access_token and refresh_token"
        )


@pytest.mark.integration
def test_fr003_refresh_returns_access_token_red() -> None:
    app, client = _create_client()
    try:
        tokens = _login(client)
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
    finally:
        asyncio.run(app.shutdown())
    if response.status_code != 200:
        raise AssertionError(f"Expected 200, got {response.status_code}")
    access_token = response.json().get("access_token", "")
    if not access_token:
        raise AssertionError("Refresh response must include a renewed access token")


@pytest.mark.integration
def test_fr004_protected_route_requires_bearer_red() -> None:
    app, client = _create_client()
    try:
        unauthorized = client.get("/api/users/me")
        tokens = _login(client)
        authorized = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
    finally:
        asyncio.run(app.shutdown())
    if unauthorized.status_code != 401:
        raise AssertionError("Expected protected endpoint to reject missing token")
    if authorized.status_code != 200:
        raise AssertionError("Expected protected endpoint to accept valid token")


@pytest.mark.integration
def test_fr005_notification_dispatch_path_red() -> None:
    app, client = _create_client()
    try:
        response = client.post("/api/users/1/notify")
    finally:
        asyncio.run(app.shutdown())
    if response.status_code != 200:
        raise AssertionError("Expected notification trigger endpoint to return 200")
    if response.json().get("status") != "sent":
        raise AssertionError("Notification endpoint should return sent status")


@pytest.mark.integration
def test_fr006_profile_image_upload_contract_red() -> None:
    app, client = _create_client()
    try:
        tokens = _login(client)
        response = client.post(
            "/api/users/me/profile-image",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            files={"file": ("photo.png", b"\x89PNG\r\n", "image/png")},
        )
    finally:
        asyncio.run(app.shutdown())
    if response.status_code != 200:
        raise AssertionError("Expected profile image upload to succeed for valid image")
    if "url" not in response.json():
        raise AssertionError("Expected profile image upload response to include url")


@pytest.mark.integration
def test_fr007_media_transform_pipeline_red() -> None:
    app, client = _create_client()
    try:
        tokens = _login(client)
        response = client.post(
            "/api/users/me/profile-image",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            files={"file": ("doc.txt", b"plain text", "text/plain")},
        )
    finally:
        asyncio.run(app.shutdown())
    if response.status_code != 400:
        raise AssertionError("Expected non-image payload to be rejected")


@pytest.mark.integration
def test_fr008_recursive_hierarchy_model_red() -> None:
    app, client = _create_client()
    try:
        response = client.get("/api/users/1/hierarchy")
    finally:
        asyncio.run(app.shutdown())
    if response.status_code != 200:
        raise AssertionError("Expected hierarchy endpoint to return 200")
    root = response.json().get("root")
    if not isinstance(root, dict):
        raise AssertionError("Expected hierarchy root object in response")


@pytest.mark.integration
def test_fr009_hierarchy_endpoint_contract_red() -> None:
    app, client = _create_client()
    try:
        response = client.get("/api/users/1/hierarchy")
    finally:
        asyncio.run(app.shutdown())
    if response.status_code != 200:
        raise AssertionError("Expected hierarchy contract endpoint to return 200")
    first_child = response.json().get("root", {}).get("children", [])
    if not isinstance(first_child, list):
        raise AssertionError("Expected hierarchy children array")


@pytest.mark.integration
def test_fr010_docs_workflow_commands_red() -> None:
    app, _client = _create_client()
    try:
        openapi: dict[str, Any] = app.asgi_app().openapi()
    finally:
        asyncio.run(app.shutdown())
    paths = openapi.get("paths", {})
    required_paths = {
        "/api/auth/login",
        "/api/auth/refresh",
        "/api/users/me/profile-image",
        "/api/users/{id}/hierarchy",
    }
    missing_paths = [path for path in required_paths if path not in paths]
    if missing_paths:
        raise AssertionError(f"Missing expected WI-002 OpenAPI paths: {missing_paths}")
