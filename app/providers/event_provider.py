"""Event & Scheduler provider — registers domain events, listeners, and scheduled tasks.

Boots after ``InfrastructureProvider`` (priority 10) and ``QueueProvider`` (priority 12)
to ensure mail and queue drivers are available.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from arvel.events import EventDispatcher
from arvel.foundation.container import Scope
from arvel.foundation.provider import ServiceProvider
from arvel.mail.contracts import MailContract
from arvel.notifications.channels.mail_channel import MailChannel
from arvel.notifications.dispatcher import NotificationDispatcher
from arvel.queue.contracts import QueueContract
from arvel.scheduler import InMemoryLockBackend, Scheduler

from app.events.user_created import UserCreated
from app.jobs.prune_expired_tokens_job import PruneExpiredTokensJob
from app.listeners.send_welcome_email_listener import SendWelcomeEmailListener

if TYPE_CHECKING:
    from arvel.foundation.application import Application
    from arvel.foundation.container import ContainerBuilder

logger = logging.getLogger(__name__)


def _make_event_dispatcher() -> EventDispatcher:
    dispatcher = EventDispatcher()
    dispatcher.register(UserCreated, SendWelcomeEmailListener)
    return dispatcher


class EventProvider(ServiceProvider):
    priority: int = 16

    async def register(self, container: ContainerBuilder) -> None:
        container.provide_factory(
            EventDispatcher, _make_event_dispatcher, scope=Scope.APP
        )

    async def boot(self, app: Application) -> None:
        event_dispatcher = await app.container.resolve(EventDispatcher)
        logger.info(
            "event_dispatcher_booted listeners=%s",
            len(event_dispatcher.listeners_for(UserCreated)),
        )

        await self._boot_scheduler(app)
        await self._boot_notification_dispatcher(app)

    @staticmethod
    async def _boot_scheduler(app: Application) -> None:
        queue = await app.container.resolve(QueueContract)
        scheduler = Scheduler(queue=queue, lock_backend=InMemoryLockBackend())
        scheduler.job(PruneExpiredTokensJob).hourly().without_overlapping()
        app.container.instance(Scheduler, scheduler)
        logger.info("scheduler_booted entries=%s", len(scheduler.entries()))

    @staticmethod
    async def _boot_notification_dispatcher(app: Application) -> None:
        mailer = await app.container.resolve(MailContract)
        channels = {"mail": MailChannel(mailer=mailer)}
        dispatcher = NotificationDispatcher(channels=channels)
        app.container.instance(NotificationDispatcher, dispatcher)
        logger.info("notification_dispatcher_booted channels=%s", list(channels.keys()))
