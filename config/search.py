"""Custom search configuration — demonstrates project-level settings discovery."""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

from arvel.foundation.config import ModuleSettings


class SearchSettings(ModuleSettings):
    """Search provider configuration.

    All values can be overridden via environment variables prefixed with ``SEARCH_``.
    """

    model_config = SettingsConfigDict(env_prefix="SEARCH_", extra="ignore")

    provider: str = "meilisearch"
    host: str = "localhost"
    port: int = 7700
    api_key: SecretStr = SecretStr("")


settings_class = SearchSettings
