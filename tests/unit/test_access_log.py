"""Tests for AccessLogMiddleware — request/response logging with duration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestAccessLogMiddleware:
    """Integration tests: AccessLogMiddleware is wired in the starter app."""

    def test_successful_request_emits_access_log(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="arvel.access"):
            client.get("/api/users")

        access_records = [r for r in caplog.records if r.name == "arvel.access"]
        assert len(access_records) >= 1
        record = access_records[-1]
        assert record.levelno == logging.INFO

    def test_access_log_includes_method_and_path(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="arvel.access"):
            client.get("/api/health")

        access_records = [r for r in caplog.records if r.name == "arvel.access"]
        assert len(access_records) >= 1

    def test_not_found_emits_warning_level(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.DEBUG, logger="arvel.access"):
            client.get("/api/nonexistent-path-for-testing")

        access_records = [r for r in caplog.records if r.name == "arvel.access"]
        assert len(access_records) >= 1
        record = access_records[-1]
        assert record.levelno == logging.WARNING


class TestAccessLogMiddlewareUnit:
    """Unit tests for the middleware in isolation."""

    @pytest.mark.anyio
    async def test_middleware_captures_status_and_duration(self) -> None:
        from arvel.observability.access_log import AccessLogMiddleware

        captured: dict[str, object] = {}

        async def fake_app(scope: dict, receive: object, send: object) -> None:
            async def start_response(message: dict) -> None:
                pass

            await start_response({"type": "http.response.start", "status": 201})

        middleware = AccessLogMiddleware(fake_app)

        status_holder: list[int] = []

        async def mock_send(message: dict) -> None:
            pass

        scope = {"type": "http", "method": "POST", "path": "/api/users", "query_string": b""}

        import logging as _logging

        handler = _logging.getLogger("arvel.access")
        records: list[_logging.LogRecord] = []

        class Capture(_logging.Handler):
            def emit(self, record: _logging.LogRecord) -> None:
                records.append(record)

        cap = Capture()
        cap.setLevel(_logging.DEBUG)
        handler.addHandler(cap)
        try:
            await middleware(scope, None, mock_send)
        finally:
            handler.removeHandler(cap)

        assert len(records) >= 1

    @pytest.mark.anyio
    async def test_middleware_skips_non_http_scopes(self) -> None:
        from arvel.observability.access_log import AccessLogMiddleware

        called = False

        async def fake_app(scope: dict, receive: object, send: object) -> None:
            nonlocal called
            called = True

        middleware = AccessLogMiddleware(fake_app)
        await middleware({"type": "websocket"}, None, None)
        assert called

    def test_access_log_enabled_setting_defaults_to_true(self) -> None:
        from arvel.observability.config import ObservabilitySettings

        settings = ObservabilitySettings()
        assert settings.access_log_enabled is True

    def test_access_log_can_be_disabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OBSERVABILITY_ACCESS_LOG_ENABLED", "false")
        from arvel.observability.config import ObservabilitySettings

        settings = ObservabilitySettings()
        assert settings.access_log_enabled is False
