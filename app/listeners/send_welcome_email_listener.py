"""SendWelcomeEmailListener — handles UserCreated by dispatching a welcome email job."""

from __future__ import annotations

import logging

from arvel.events import Listener
from arvel.queue.contracts import QueueContract
from arvel.queue.manager import QueueManager

from app.events.user_created import UserCreated
from app.jobs.send_welcome_email_job import SendWelcomeEmailJob

logger = logging.getLogger(__name__)


def _resolve_queue() -> QueueContract:
    """Build the queue driver from environment config.

    Listeners are instantiated by the EventDispatcher with no constructor
    args, so they can't receive DI.  This uses the framework's QueueManager
    which reads QueueSettings from env vars — the same factory the
    QueueProvider uses.
    """
    return QueueManager().create_driver()


class SendWelcomeEmailListener(Listener):
    """Dispatches ``SendWelcomeEmailJob`` when a ``UserCreated`` event fires.

    The job is executed synchronously in test mode (``QUEUE_DRIVER=sync``)
    and asynchronously in production (via Taskiq or another broker).
    """

    async def handle(self, event: UserCreated) -> None:
        queue = _resolve_queue()
        job = SendWelcomeEmailJob(
            user_id=event.user_id,
            email=event.email,
            name=event.name,
        )
        await queue.dispatch(job)
        logger.info("welcome_email_job_dispatched user_id=%s", event.user_id)
