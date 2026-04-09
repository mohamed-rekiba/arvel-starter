"""Observability configuration — logging channels, levels, request ID, health checks.

Loaded by ``ObservabilityProvider`` at boot time.  Environment variables
are prefixed with ``OBSERVABILITY_`` (see ``ObservabilitySettings``).
"""

from __future__ import annotations

from arvel.observability.config import ObservabilitySettings


class StarterObservabilitySettings(ObservabilitySettings):
    """Starter-specific overrides (none for now — all values come from env)."""


settings_class = StarterObservabilitySettings
