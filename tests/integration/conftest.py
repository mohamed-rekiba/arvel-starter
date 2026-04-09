"""Integration test conftest — marks all tests here as integration and
skips when live services aren't available."""

from __future__ import annotations

import socket

import pytest

pytestmark = pytest.mark.integration

_SERVICE_PORTS: dict[str, tuple[str, int]] = {
    "redis": ("127.0.0.1", 6379),
    "smtp": ("127.0.0.1", 1025),
    "s3": ("127.0.0.1", 9000),
}


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture(autouse=True)
def _skip_without_service(request: pytest.FixtureRequest) -> None:
    """Skip tests marked with service names when the service isn't reachable."""
    for marker_name, (host, port) in _SERVICE_PORTS.items():
        if request.node.get_closest_marker(marker_name) and not _port_open(host, port):
            pytest.skip(f"{marker_name} not available at {host}:{port}")
