"""Broadcast configuration — typed settings with BROADCAST_ env prefix."""

from __future__ import annotations

from typing import ClassVar

from pydantic_settings import SettingsConfigDict

from arvel.foundation.config import ModuleSettings


class BroadcastSettings(ModuleSettings):
    """Broadcast driver configuration.

    All values can be overridden via environment variables prefixed with ``BROADCAST_``.
    """

    model_config = SettingsConfigDict(env_prefix="BROADCAST_", extra="ignore")
    config_name: ClassVar[str] = "broadcasting"

    driver: str = "null"
    auth_endpoint: str = "/broadcasting/auth"


settings_class = BroadcastSettings
