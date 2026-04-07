"""WI-011 tests — RequestIdMiddleware and structured logging (Epic 008, Story 2).

Validates that X-Request-ID is propagated and generated correctly.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestRequestIdMiddleware:
    """Tests for RequestIdMiddleware on HTTP requests."""

    def test_response_includes_x_request_id_header(self, client: TestClient) -> None:
        response = client.get("/api/users")
        assert "x-request-id" in response.headers
        rid = response.headers["x-request-id"]
        uuid.UUID(rid)

    def test_generated_request_id_is_uuid7(self, client: TestClient) -> None:
        response = client.get("/api/health")
        rid = response.headers.get("x-request-id", "")
        parsed = uuid.UUID(rid)
        assert parsed.version == 7

    def test_provided_request_id_is_echoed_back(self, client: TestClient) -> None:
        custom_id = str(uuid.uuid7())
        response = client.get(
            "/api/users",
            headers={"X-Request-ID": custom_id},
        )
        assert response.headers["x-request-id"] == custom_id

    def test_invalid_request_id_generates_new_one(self, client: TestClient) -> None:
        response = client.get(
            "/api/users",
            headers={"X-Request-ID": "not-a-uuid"},
        )
        rid = response.headers.get("x-request-id", "")
        assert rid != "not-a-uuid"
        uuid.UUID(rid)

    def test_different_requests_get_different_ids(self, client: TestClient) -> None:
        r1 = client.get("/api/users")
        r2 = client.get("/api/users")
        id1 = r1.headers.get("x-request-id", "")
        id2 = r2.headers.get("x-request-id", "")
        assert id1 != id2


class TestObservabilityConfig:
    """Tests for observability configuration settings."""

    def test_observability_settings_load_defaults(self) -> None:
        from arvel.observability.config import ObservabilitySettings

        settings = ObservabilitySettings()
        assert settings.log_level == "info" or settings.log_level == "debug"
        assert settings.health_timeout > 0

    def test_redact_patterns_include_sensitive_keys(self) -> None:
        from arvel.observability.config import ObservabilitySettings

        settings = ObservabilitySettings()
        patterns = settings.log_redact_patterns
        assert "password" in patterns
        assert "token" in patterns
        assert "secret" in patterns

    def test_redact_processor_redacts_sensitive_fields(self) -> None:
        from arvel.observability.logging import RedactProcessor

        processor = RedactProcessor(patterns=["password", "token"])
        event = {
            "event": "test",
            "password": "s3cret",
            "auth_token": "abc123",
            "name": "Alice",
        }
        result = processor(None, None, event)
        assert result["password"] == "***"
        assert result["auth_token"] == "***"
        assert result["name"] == "Alice"

    def test_context_processor_injects_request_id(self) -> None:
        from arvel.context import Context
        from arvel.observability.logging import ContextProcessor

        Context.flush()
        Context.add("request_id", "test-rid-123")
        try:
            processor = ContextProcessor()
            event: dict[str, object] = {"event": "test"}
            result = processor(None, None, event)
            assert result["request_id"] == "test-rid-123"
        finally:
            Context.flush()

    def test_context_processor_injects_custom_keys(self) -> None:
        from arvel.context import Context
        from arvel.observability.logging import ContextProcessor

        Context.flush()
        Context.add("request_id", "rid-456")
        Context.add("tenant_id", "tenant-abc")
        Context.add("user_id", "user-789")
        try:
            processor = ContextProcessor()
            event: dict[str, object] = {"event": "test"}
            result = processor(None, None, event)
            assert result["request_id"] == "rid-456"
            assert result["tenant_id"] == "tenant-abc"
            assert result["user_id"] == "user-789"
        finally:
            Context.flush()

    def test_context_processor_does_not_overwrite_explicit_keys(self) -> None:
        from arvel.context import Context
        from arvel.observability.logging import ContextProcessor

        Context.flush()
        Context.add("request_id", "from-context")
        try:
            processor = ContextProcessor()
            event: dict[str, object] = {"event": "test", "request_id": "explicit-value"}
            result = processor(None, None, event)
            assert result["request_id"] == "explicit-value"
        finally:
            Context.flush()

    def test_request_id_processor_alias_is_context_processor(self) -> None:
        from arvel.observability.logging import ContextProcessor, RequestIdProcessor

        assert RequestIdProcessor is ContextProcessor
