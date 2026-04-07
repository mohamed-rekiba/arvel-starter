from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from arvel.foundation.application import Application


def _openapi_schema() -> dict[str, Any]:
    base_path = Path(__file__).resolve().parents[2]
    app = asyncio.run(Application.create(base_path, testing=True))
    try:
        return app.asgi_app().openapi()
    finally:
        asyncio.run(app.shutdown())


def _paths_map(openapi: dict[str, Any]) -> dict[str, Any]:
    paths = openapi.get("paths")
    if not isinstance(paths, dict):
        raise AssertionError("OpenAPI paths should be a dictionary")
    return paths


def _users_path(paths: dict[str, Any]) -> dict[str, Any]:
    users_path = paths.get("/api/users")
    if not isinstance(users_path, dict):
        raise AssertionError("Expected /api/users path in OpenAPI")
    return users_path


def _schema_from_response(operation: dict[str, Any]) -> dict[str, Any]:
    schema = (
        operation.get("responses", {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    if not isinstance(schema, dict):
        raise AssertionError("Expected 200 response schema dictionary")
    return schema


def test_openapi_includes_typed_user_and_ping_schemas() -> None:
    openapi = _openapi_schema()
    paths = _paths_map(openapi)
    users_path = _users_path(paths)

    users_index = users_path.get("get")
    if not isinstance(users_index, dict):
        raise AssertionError("Expected /api/users GET operation in OpenAPI")
    users_response = _schema_from_response(users_index)
    response_ref = users_response.get("$ref", "")
    if not str(response_ref).endswith("/PaginatedUserResponse"):
        raise AssertionError(
            "Expected /api/users GET response schema to reference PaginatedUserResponse"
        )

    users_create = users_path.get("post")
    if not isinstance(users_create, dict):
        raise AssertionError("Expected /api/users POST operation in OpenAPI")
    create_body = (
        users_create.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    if not isinstance(create_body, dict):
        raise AssertionError("Expected /api/users POST request body schema dictionary")
    create_ref = create_body.get("$ref", "")
    if not str(create_ref).endswith("/UserCreateRequest"):
        raise AssertionError(
            "Expected /api/users POST request body to reference UserCreateRequest"
        )

    health_path = paths.get("/api/health") or paths.get("/health")
    if not isinstance(health_path, dict):
        raise AssertionError("Expected /api/health or /health path in OpenAPI")

    health_op = health_path.get("get")
    if not isinstance(health_op, dict):
        raise AssertionError("Expected health GET operation in OpenAPI")
    ping_schema = _schema_from_response(health_op)
    ping_ref = ping_schema.get("$ref", "")
    if not (
        str(ping_ref).endswith("/PingResponse")
        or str(ping_ref).endswith("/HealthEndpointPayload")
    ):
        raise AssertionError(
            "Expected health GET response schema to reference PingResponse or HealthEndpointPayload"
        )
