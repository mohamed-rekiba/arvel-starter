"""Custom search configuration — demonstrates project-level settings discovery."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import SettingsConfigDict

from arvel.foundation.config import ModuleSettings


class SearchSettings(ModuleSettings):
    """Search provider configuration.

    All values can be overridden via environment variables prefixed with ``SEARCH_``.
    """

    model_config = SettingsConfigDict(env_prefix="SEARCH_", extra="ignore")

    driver: Literal["null", "collection", "database", "meilisearch", "elasticsearch"] = "collection"
    prefix: str = ""
    queue_sync: bool = False

    meilisearch_url: str = "http://localhost:7700"
    meilisearch_key: str = ""
    meilisearch_timeout: int = 5

    elasticsearch_hosts: str = "http://localhost:9200"
    elasticsearch_verify_certs: bool = True


settings_class = SearchSettings
