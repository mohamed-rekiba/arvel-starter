"""Create auth refresh token persistence table.

This migration is shipped by the Arvel auth module.  You can customise
it after publishing — the framework will not overwrite it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from arvel.data import ForeignKeyAction, Schema

if TYPE_CHECKING:
    from arvel.data import Blueprint


def upgrade() -> None:
    def auth_refresh_tokens(table: Blueprint) -> None:
        table.id()
        table.foreign_id("user_id").references(
            "users",
            "id",
            on_delete=ForeignKeyAction.CASCADE,
            on_update=ForeignKeyAction.CASCADE,
        ).nullable().index()
        table.string("token_hash")
        table.datetime("issued_at")
        table.datetime("expires_at")
        table.datetime("revoked_at").nullable()

    Schema.create("auth_refresh_tokens", auth_refresh_tokens)


def downgrade() -> None:
    Schema.drop("auth_refresh_tokens")
