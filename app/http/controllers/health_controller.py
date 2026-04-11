"""Health controller — thin wrapper providing /api/health.

The framework's ``ObservabilityProvider`` registers the real ``/health``
endpoint.  This controller mirrors it under ``/api/v1/health`` for API
consistency, reusing the same health check classes.

Only checks for enabled services are registered — no-op drivers
(memory cache, sync queue, null storage) are excluded.
"""

from __future__ import annotations

import logging

from arvel.cache.config import CacheSettings
from arvel.http import BaseController, Response, route, status  # noqa: TC001
from arvel.observability.health import (
    HealthEndpointPayload,
    HealthRegistry,
    HealthStatus,
)
from arvel.observability.integration_health import (
    CacheHealthCheck,
    DatabaseHealthCheck,
    QueueHealthCheck,
    StorageHealthCheck,
)
from arvel.queue.config import QueueSettings
from arvel.storage.config import StorageSettings

logger = logging.getLogger(__name__)


def _build_registry() -> HealthRegistry:
    registry = HealthRegistry(timeout=5.0)
    registry.register(DatabaseHealthCheck())

    try:
        if CacheSettings().driver not in {"memory", "null"}:
            registry.register(CacheHealthCheck())
    except Exception:  # pragma: no cover
        logger.debug("cache health check registration skipped", exc_info=True)

    try:
        if QueueSettings().driver not in {"sync", "null"}:
            registry.register(QueueHealthCheck())
    except Exception:  # pragma: no cover
        logger.debug("queue health check registration skipped", exc_info=True)

    try:
        if StorageSettings().driver not in {"null"}:
            registry.register(StorageHealthCheck())
    except Exception:  # pragma: no cover
        logger.debug("storage health check registration skipped", exc_info=True)

    return registry


_registry = _build_registry()


class HealthController(BaseController):
    prefix = "/health"
    tags = ("health",)
    description = "Health endpoint backed by framework HealthRegistry."

    @route.get(
        "/",
        response_model=HealthEndpointPayload,
        summary="Aggregated health checks",
        description="Returns health statuses for all enabled services.",
        operation_id="health_check",
    )
    async def check(self, response: Response) -> HealthEndpointPayload:
        result = await _registry.run_all()
        if result.status == HealthStatus.UNHEALTHY:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return result
