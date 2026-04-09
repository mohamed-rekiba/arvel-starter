"""Create notifications table for database notification channel.

This migration is shipped by the Arvel notifications module.  You can
customise it after publishing — the framework will not overwrite it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from arvel.data import Schema

if TYPE_CHECKING:
    from arvel.data import Blueprint


def upgrade() -> None:
    def notifications(table: Blueprint) -> None:
        table.id()
        table.string("notifiable_type").index()
        table.integer("notifiable_id").index()
        table.string("type").index()
        table.text("data")
        table.datetime("read_at").nullable()
        table.timestamps()

    Schema.create("notifications", notifications)


def downgrade() -> None:
    Schema.drop("notifications")
