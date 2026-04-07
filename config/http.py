"""HTTP module configuration — middleware aliases, global middleware, trusted proxies."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from arvel.foundation.config import ModuleSettings


class HttpSettings(ModuleSettings):
    """Configuration slice for the HTTP and routing layer.

    Environment variables are prefixed with ``HTTP_``.
    """

    model_config = SettingsConfigDict(env_prefix="HTTP_", extra="ignore")

    middleware_aliases: dict[str, str] = Field(default_factory=dict)
    middleware_groups: dict[str, list[str]] = Field(default_factory=dict)
    global_middleware: list[tuple[str, int]] = Field(default_factory=list)
    trusted_proxies: list[str] = Field(default_factory=list)


settings_class = HttpSettings
