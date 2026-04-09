"""User factory for deterministic test data.

Uses the starter's existing ``make_user`` factory function and wraps it
for convenient batch creation within test transactions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from arvel.security.contracts import HasherContract
from arvel.security.hashing import BcryptHasher

from app.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_hasher: HasherContract = BcryptHasher(rounds=4)

_counter = 0


def _next_seq() -> int:
    global _counter  # noqa: PLW0603
    _counter += 1
    return _counter


def make_user(
    *,
    name: str | None = None,
    email: str | None = None,
    password: str = "password123",
    parent_id: int | None = None,
) -> User:
    """Build a User instance with deterministic defaults.

    Passwords are hashed with bcrypt (low rounds for test speed).
    Sequential email addresses avoid unique constraint collisions.
    """
    seq = _next_seq()
    return User(
        name=name or f"Test User {seq}",
        email=email or f"user-{seq}@test.com",
        password=_hasher.make(password),
        parent_id=parent_id,
    )


async def create_user(
    session: AsyncSession,
    *,
    name: str | None = None,
    email: str | None = None,
    password: str = "password123",
    parent_id: int | None = None,
) -> User:
    """Create and persist a User within the given session."""
    user = make_user(name=name, email=email, password=password, parent_id=parent_id)
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user
