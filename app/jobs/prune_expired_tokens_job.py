"""PruneExpiredTokensJob — scheduled task to clean up expired refresh tokens."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from arvel.queue import Job

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult

logger = logging.getLogger(__name__)


class PruneExpiredTokensJob(Job):
    """Deletes expired refresh tokens from the ``auth_refresh_tokens`` table.

    Scheduled hourly via the ``Scheduler``. Uses a direct SQL delete
    so the job stays lightweight and doesn't load token models into memory.
    """

    max_retries: int = 1
    queue_name: str = "maintenance"

    async def handle(self) -> None:
        from arvel.data import ArvelModel

        session_resolver = ArvelModel._session_resolver
        if session_resolver is None:
            logger.warning("prune_tokens_skipped: no session resolver")
            return

        async with session_resolver() as session:
            table = ArvelModel.metadata.tables.get("auth_refresh_tokens")
            if table is None:
                logger.info("prune_tokens_skipped: table does not exist")
                return

            now = datetime.now(UTC)
            # SA async execute() returns CursorResult for DML statements
            result = cast(
                "CursorResult[tuple[()]]",
                await session.execute(
                    table.delete().where(table.c.expires_at < now),
                ),
            )
            await session.commit()
            logger.info("prune_tokens_complete deleted=%s", result.rowcount)
