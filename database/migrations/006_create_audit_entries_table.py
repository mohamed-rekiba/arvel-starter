"""Create audit_entries table for the Auditable mixin.

This migration is shipped by the Arvel audit module.  You can customise
it after publishing — the framework will not overwrite it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from arvel.data import Schema

if TYPE_CHECKING:
    from arvel.data import Blueprint


def upgrade() -> None:
    def audit_entries(table: Blueprint) -> None:
        table.id()
        table.string("actor_id").nullable().index()
        table.string("action")
        table.string("model_type").index()
        table.string("model_id").index()
        table.text("old_values").nullable()
        table.text("new_values").nullable()
        table.datetime("timestamp").index()
        table.timestamps()

    Schema.create("audit_entries", audit_entries)


def downgrade() -> None:
    Schema.drop("audit_entries")
