"""Database seeder — populates the starter user hierarchy.

Seeds a four-node tree used by the hierarchy endpoint demo:

    root
    ├── child-a
    │   └── grandchild-a1
    └── child-b

Also seeds a ``root@example.com`` user used by auth tests.
Emails use the ``@starter.local`` domain as stable identifiers for
idempotency.  Names and passwords are Faker-generated via the
``make_user`` factory — every seed run produces realistic, randomized
field values while the tree structure remains deterministic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.models.user import User
from arvel.data.seeder import Seeder
from database.factories.user_factory import make_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from arvel.data.transaction import Transaction

_SEED_EMAILS: tuple[str, ...] = (
    "root@starter.local",
    "child-a@starter.local",
    "child-b@starter.local",
    "grandchild-a1@starter.local",
)

_AUTH_TEST_EMAIL = "root@example.com"
_SEED_PASSWORD = "password"  # noqa: S105


class DatabaseSeeder(Seeder):
    async def run(self, tx: Transaction) -> None:
        session = tx._session

        root = await self._ensure_user(session, email=_SEED_EMAILS[0], password=_SEED_PASSWORD)
        child_a = await self._ensure_user(session, email=_SEED_EMAILS[1], parent_id=root.id)
        await self._ensure_user(session, email=_SEED_EMAILS[2], parent_id=root.id)
        await self._ensure_user(session, email=_SEED_EMAILS[3], parent_id=child_a.id)

        await self._ensure_user(
            session,
            email=_AUTH_TEST_EMAIL,
            password=_SEED_PASSWORD,
            name="Root User",
        )

    @staticmethod
    async def _ensure_user(
        session: AsyncSession,
        *,
        email: str,
        password: str | None = None,
        name: str | None = None,
        parent_id: int | None = None,
    ) -> User:
        """Return existing user by email, or create one with Faker defaults."""
        existing = await User.query(session).where(User.email == email).order_by(User.id).first()
        if existing is not None:
            return existing

        user = make_user(email=email, password=password, name=name, parent_id=parent_id)
        session.add(user)
        await session.flush()
        return user
