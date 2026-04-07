"""Shared fixtures for starter tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from arvel.foundation.application import Application

if TYPE_CHECKING:
    from collections.abc import Generator


def _starter_root() -> Path:
    return Path(__file__).resolve().parents[1]


async def _create_and_seed(root: Path) -> Application:
    application = await Application.create(root, testing=True)

    from arvel.data.transaction import Transaction
    from sqlalchemy.ext.asyncio import AsyncSession

    session = await application.container.resolve(AsyncSession)
    tx = Transaction(session=session)
    from database.seeders.database_seeder import DatabaseSeeder

    seeder = DatabaseSeeder()
    await seeder.run(tx)
    await session.commit()
    await session.close()
    return application


@pytest.fixture(scope="session")
def app() -> Generator[Application]:
    application = asyncio.run(_create_and_seed(_starter_root()))
    yield application
    asyncio.run(application.shutdown())


@pytest.fixture(scope="session")
def client(app: Application) -> TestClient:
    return TestClient(app.asgi_app())


@pytest.fixture(scope="session")
def auth_token(client: TestClient) -> str:
    """Return a valid JWT access token from the login endpoint."""
    response = client.post(
        "/api/auth/login",
        json={"email": "root@example.com", "password": "password"},
    )
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def auth_headers(auth_token: str) -> dict[str, str]:
    """Return Authorization headers with a valid JWT."""
    return {"Authorization": f"Bearer {auth_token}"}
