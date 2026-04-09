"""Application-level configuration — OpenAPI metadata and security schemes."""

from __future__ import annotations

from typing import Any

from arvel.app.config import AppSettings as BaseAppSettings
from pydantic import Field


class AppSettings(BaseAppSettings):  # type: ignore[no-redef]
    """Starter-specific defaults layered on top of the framework's AppSettings."""

    app_openapi_security_schemes: dict[str, dict[str, Any]] | None = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT access token (from /api/auth/login)",
        },
    }

    app_openapi_global_security: list[dict[str, list[str]]] | None = [
        {"BearerAuth": []},
    ]

    app_openapi_tags: list[dict[str, Any]] | None = Field(  # type: ignore[assignment]
        default=[
            {"name": "auth", "description": "Login and token refresh"},
            {
                "name": "users",
                "description": "User management, profile, media, search, and hierarchy",
            },
            {"name": "health", "description": "Health checks"},
            {"name": "infrastructure", "description": "Cache, lock, and storage demos"},
        ],
    )


settings_class = AppSettings
