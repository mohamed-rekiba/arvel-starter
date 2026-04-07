"""Create the users table.

This migration is shipped by the Arvel auth module.  You can add custom
columns by editing this file — the framework will not overwrite it once
published.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from arvel.data import Schema

if TYPE_CHECKING:
    from arvel.data import Blueprint


def upgrade() -> None:
    def users(table: Blueprint) -> None:
        table.id()
        table.string("name")
        table.string("email").unique()
        table.string("password")
        table.datetime("email_verified_at").nullable()
        table.soft_deletes()
        table.timestamps()

    Schema.create("users", users)


def downgrade() -> None:
    Schema.drop("users")
