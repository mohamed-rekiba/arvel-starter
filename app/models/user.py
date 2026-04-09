"""User model — demonstrates relationships, soft deletes, mass assignment, search, and audit."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from arvel.audit import Auditable
from arvel.data import ArvelModel, SoftDeletes, String, mapped_column
from arvel.search import Searchable
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, relationship  # noqa: TC002


class User(SoftDeletes, Searchable, Auditable, ArvelModel):
    """Application user with self-referential parent/children hierarchy.

    Uses SA ``relationship()`` directly for the self-referential join
    because the framework's ``has_many``/``belongs_to`` helpers don't
    support ``remote_side`` needed for self-referencing FKs.

    ``Searchable`` mixin enables full-text search via ``User.search("query")``.
    ``Auditable`` mixin enables automatic audit trail recording.
    The ``__searchable__`` list controls which fields are indexed.
    The ``__audit_redact__`` set controls which fields are redacted in audit entries.
    """

    __fillable__: ClassVar[set[str]] = {"name", "email", "password", "parent_id"}
    __searchable__: ClassVar[list[str]] = ["name", "email"]
    __audit_redact__: ClassVar[set[str]] = {"password"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password: Mapped[str] = mapped_column(String(255))
    email_verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    children: Mapped[list[User]] = relationship(
        back_populates="parent",
        lazy="noload",
        remote_side="User.parent_id",
        foreign_keys="User.parent_id",
    )
    parent: Mapped[User | None] = relationship(
        back_populates="children",
        lazy="noload",
        remote_side="User.id",
        foreign_keys="User.parent_id",
    )
