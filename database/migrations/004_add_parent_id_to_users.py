"""Add parent_id FK for hierarchical (self-referential) users."""

from __future__ import annotations

from typing import TYPE_CHECKING

from arvel.data import ForeignKeyAction, Schema

if TYPE_CHECKING:
    from arvel.data import Blueprint


def upgrade() -> None:
    def add_parent_id(table: Blueprint) -> None:
        table.foreign_id("parent_id").references(
            "users",
            "id",
            on_delete=ForeignKeyAction.SET_NULL,
            on_update=ForeignKeyAction.CASCADE,
        ).nullable().index()

    Schema.table("users", add_parent_id)


def downgrade() -> None:
    Schema.drop_columns("users", "parent_id")
