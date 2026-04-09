"""UserCreated domain event — fired after a new user is persisted."""

from __future__ import annotations

from arvel.events import Event


class UserCreated(Event):
    """Carries the essential data about a newly created user.

    Intentionally excludes the password — event payloads must never
    contain credentials.
    """

    user_id: int
    email: str
    name: str
