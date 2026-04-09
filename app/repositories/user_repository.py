"""Typed repository for the User model.

Demonstrates:
- ``Repository[T]`` pattern with session encapsulation
- Custom query methods using ``self.query()``
- Observer dispatch on mutating operations (via base class)
"""

from __future__ import annotations

from arvel.data import Repository

from app.models.user import User


class UserRepository(Repository[User]):
    """Typed data access for User records."""

    async def find_by_email(self, email: str) -> User | None:
        """Look up a user by exact email match."""
        return await self.query().where(User.email == email).order_by(User.id).first()
