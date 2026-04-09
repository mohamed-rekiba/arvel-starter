"""Observer for User model lifecycle events.

Demonstrates:
- ``ModelObserver[T]`` with pre-hooks (``creating``) that can abort
- Post-hooks (``created``, ``updated``) for side effects
- Email normalisation as a real-world pre-create validation
- Domain event dispatch (``UserCreated``) via the shared ``EventDispatcher``
- Search indexing via ``SearchEngine``
- Broadcasting via ``BroadcastContract``

Services are injected via the constructor at registration time in ``DataProvider``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from arvel.broadcasting.channels import Channel
from arvel.data import ModelObserver

from app.events.user_created import UserCreated
from app.models.user import User

if TYPE_CHECKING:
    from arvel.broadcasting.contracts import BroadcastContract
    from arvel.events import EventDispatcher
    from arvel.search.contracts import SearchEngine

logger = logging.getLogger(__name__)


class UserObserver(ModelObserver[User]):
    """Listens to User lifecycle events.

    Infrastructure services are injected at registration time so the
    observer doesn't need to resolve them from the container per-call.
    """

    def __init__(
        self,
        *,
        search_engine: SearchEngine | None = None,
        broadcaster: BroadcastContract | None = None,
        event_dispatcher: EventDispatcher | None = None,
    ) -> None:
        self._search_engine = search_engine
        self._broadcaster = broadcaster
        self._event_dispatcher = event_dispatcher

    async def creating(self, instance: User) -> bool:
        """Normalize email to lowercase before persisting."""
        instance.email = instance.email.strip().lower()
        return True

    async def created(self, instance: User) -> None:
        logger.info("user_created id=%s email=%s", instance.id, instance.email)
        await self._index_user(instance)
        await self._broadcast_user_created(instance)
        await self._dispatch_user_created_event(instance)

    async def updating(self, instance: User) -> bool:
        if hasattr(instance, "email") and instance.email:
            instance.email = instance.email.strip().lower()
        return True

    async def updated(self, instance: User) -> None:
        logger.info("user_updated id=%s", instance.id)
        await self._index_user(instance)

    async def _index_user(self, user: User) -> None:
        if self._search_engine is None:
            return
        try:
            doc = user.to_searchable_array()
            await self._search_engine.upsert_documents(User.search_index_name(), [doc])
        except Exception:
            logger.exception("search_index_failed id=%s", user.id)

    async def _broadcast_user_created(self, user: User) -> None:
        if self._broadcaster is None:
            return
        try:
            await self._broadcaster.broadcast(
                [Channel("users")],
                "user.created",
                {"user_id": user.id, "name": user.name, "email": user.email},
            )
        except Exception:
            logger.exception("broadcast_user_created_failed id=%s", user.id)

    async def _dispatch_user_created_event(self, user: User) -> None:
        if self._event_dispatcher is None:
            return
        try:
            await self._event_dispatcher.dispatch(
                UserCreated(user_id=user.id, email=user.email, name=user.name),
            )
        except Exception:
            logger.exception("user_created_event_dispatch_failed id=%s", user.id)
