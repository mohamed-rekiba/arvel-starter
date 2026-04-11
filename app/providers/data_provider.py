"""Data layer provider — registers model observers and creates the DB schema.

Boots after ``DatabaseServiceProvider`` (priority 5) and infrastructure
providers (priority 10-12) to ensure the session resolver, observer
registry, and infrastructure services are available.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.models.user import User
from app.observers.user_observer import UserObserver
from arvel.broadcasting.contracts import BroadcastContract
from arvel.data import ArvelModel
from arvel.events import EventDispatcher
from arvel.foundation.provider import ServiceProvider
from arvel.search.contracts import SearchEngine

if TYPE_CHECKING:
    from arvel.data import ObserverRegistry
    from arvel.foundation.application import Application

logger = logging.getLogger(__name__)


class DataProvider(ServiceProvider):
    priority: int = 20

    async def boot(self, app: Application) -> None:
        search_engine = await self._resolve_optional(app, SearchEngine)
        broadcaster = await self._resolve_optional(app, BroadcastContract)
        event_dispatcher = await self._resolve_optional(app, EventDispatcher)

        observer = UserObserver(
            search_engine=search_engine,
            broadcaster=broadcaster,
            event_dispatcher=event_dispatcher,
        )

        registry = ArvelModel._observer_registry_resolver
        if registry is not None:
            obs_registry: ObserverRegistry = registry()
            obs_registry.register(User, observer)
            logger.info("user_observer_registered")

        await self._ensure_schema(app)

    @staticmethod
    async def _resolve_optional[T](app: Application, interface: type[T]) -> T | None:
        try:
            return await app.container.resolve(interface)
        except Exception:
            return None

    @staticmethod
    async def _ensure_schema(app: Application) -> None:
        """Create tables from ORM metadata if they don't exist (dev/test convenience)."""
        from sqlalchemy.ext.asyncio import AsyncEngine

        engine = await app.container.resolve(AsyncEngine)
        async with engine.begin() as conn:
            await conn.run_sync(ArvelModel.metadata.create_all)
        logger.info("schema_ensured")
