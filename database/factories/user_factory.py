from __future__ import annotations

from arvel.security.contracts import HasherContract
from arvel.security.hashing import BcryptHasher
from faker import Faker

from app.models.user import User

fake = Faker()

_hasher: HasherContract = BcryptHasher(rounds=4)


def make_user(
    *,
    user_id: int | None = None,
    name: str | None = None,
    email: str | None = None,
    password: str | None = None,
    parent_id: int | None = None,
) -> User:
    """Build a User instance with faker-generated defaults.

    All fields can be overridden explicitly for deterministic seeding.
    Passwords are hashed with bcrypt (low rounds for test speed).
    """
    raw_password = password or fake.password(length=16)
    payload: dict[str, object] = {
        "name": name or fake.name(),
        "email": email or fake.unique.email(),
        "password": _hasher.make(raw_password),
        "parent_id": parent_id,
    }
    if user_id is not None:
        payload["id"] = user_id
    return User(**payload)
