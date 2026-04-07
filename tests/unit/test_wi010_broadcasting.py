"""WI-010 Broadcasting tests — MemoryBroadcaster, BroadcastFake, channel authorization.

Covers Epic 007 Story 3: BroadcastContract demonstration with
MemoryBroadcaster and channel-level authorization.
"""

from __future__ import annotations

import pytest

from arvel.auth.policy import AuthContext
from arvel.broadcasting import (
    Channel,
    ChannelAuthorizer,
    PresenceChannel,
    PrivateChannel,
)
from arvel.broadcasting.drivers.memory_driver import MemoryBroadcaster
from arvel.broadcasting.fake import BroadcastFake


class TestMemoryBroadcasterBasics:
    @pytest.mark.anyio
    async def test_broadcast_records_event(self) -> None:
        broadcaster = MemoryBroadcaster()
        await broadcaster.broadcast(
            [Channel("users")],
            "user.created",
            {"user_id": 1, "name": "Alice"},
        )
        assert len(broadcaster.broadcasts) == 1
        entry = broadcaster.broadcasts[0]
        assert entry["event"] == "user.created"
        assert "users" in entry["channels"]
        assert entry["data"]["user_id"] == 1

    @pytest.mark.anyio
    async def test_broadcast_to_multiple_channels(self) -> None:
        broadcaster = MemoryBroadcaster()
        await broadcaster.broadcast(
            [Channel("users"), Channel("admins")],
            "user.created",
            {"user_id": 1},
        )
        entry = broadcaster.broadcasts[0]
        assert "users" in entry["channels"]
        assert "admins" in entry["channels"]

    @pytest.mark.anyio
    async def test_flush_clears_broadcasts(self) -> None:
        broadcaster = MemoryBroadcaster()
        await broadcaster.broadcast([Channel("ch")], "ev", {})
        broadcaster.flush()
        assert broadcaster.broadcasts == []


class TestBroadcastFakeAssertions:
    @pytest.mark.anyio
    async def test_assert_broadcast_passes_for_sent_event(self) -> None:
        fake = BroadcastFake()
        await fake.broadcast([Channel("users")], "user.created", {"id": 1})
        fake.assert_broadcast("user.created")

    @pytest.mark.anyio
    async def test_assert_broadcast_with_channel_filter(self) -> None:
        fake = BroadcastFake()
        await fake.broadcast([Channel("users")], "user.created", {"id": 1})
        fake.assert_broadcast("user.created", channel="users")

    @pytest.mark.anyio
    async def test_assert_broadcast_fails_for_unsent_event(self) -> None:
        fake = BroadcastFake()
        with pytest.raises(AssertionError, match="never broadcast"):
            fake.assert_broadcast("missing.event")

    @pytest.mark.anyio
    async def test_assert_broadcast_on_passes(self) -> None:
        fake = BroadcastFake()
        await fake.broadcast([Channel("ch1")], "ev", {})
        fake.assert_broadcast_on("ch1")

    @pytest.mark.anyio
    async def test_assert_broadcast_on_fails_for_wrong_channel(self) -> None:
        fake = BroadcastFake()
        await fake.broadcast([Channel("ch1")], "ev", {})
        with pytest.raises(AssertionError, match="No broadcast found"):
            fake.assert_broadcast_on("wrong-channel")

    @pytest.mark.anyio
    async def test_assert_nothing_broadcast_passes_when_empty(self) -> None:
        fake = BroadcastFake()
        fake.assert_nothing_broadcast()

    @pytest.mark.anyio
    async def test_assert_nothing_broadcast_fails_when_events_exist(self) -> None:
        fake = BroadcastFake()
        await fake.broadcast([Channel("ch")], "ev", {})
        with pytest.raises(AssertionError, match="Expected no broadcasts"):
            fake.assert_nothing_broadcast()

    @pytest.mark.anyio
    async def test_assert_broadcast_count(self) -> None:
        fake = BroadcastFake()
        for _ in range(3):
            await fake.broadcast([Channel("ch")], "user.created", {})
        fake.assert_broadcast_count("user.created", 3)


class TestChannelTypes:
    def test_public_channel_has_name(self) -> None:
        ch = Channel("public-feed")
        assert ch.name == "public-feed"

    def test_private_channel_is_channel_subclass(self) -> None:
        ch = PrivateChannel("users.42")
        assert isinstance(ch, Channel)
        assert ch.name == "users.42"

    def test_presence_channel_is_channel_subclass(self) -> None:
        ch = PresenceChannel("room.lobby")
        assert isinstance(ch, Channel)
        assert ch.name == "room.lobby"


def _auth(user_id: str) -> AuthContext:
    """Build an AuthContext with ``sub`` set for channel authorization tests."""
    return AuthContext(user=None, sub=user_id)


class TestChannelAuthorizer:
    def test_public_channel_always_authorized(self) -> None:
        import asyncio

        authorizer = ChannelAuthorizer()
        result = asyncio.run(authorizer.authorize(_auth("42"), Channel("public")))
        assert result is True

    def test_private_channel_with_matching_callback(self) -> None:
        import asyncio

        authorizer = ChannelAuthorizer()
        authorizer.private(
            "users.{id}",
            lambda ctx, id: ctx.sub == id,
        )
        result = asyncio.run(
            authorizer.authorize(_auth("42"), PrivateChannel("users.42"))
        )
        assert result is True

    def test_private_channel_with_mismatched_callback(self) -> None:
        import asyncio

        authorizer = ChannelAuthorizer()
        authorizer.private(
            "users.{id}",
            lambda ctx, id: ctx.sub == id,
        )
        result = asyncio.run(
            authorizer.authorize(_auth("42"), PrivateChannel("users.99"))
        )
        assert result is False

    def test_unregistered_private_channel_returns_false(self) -> None:
        import asyncio

        authorizer = ChannelAuthorizer()
        result = asyncio.run(
            authorizer.authorize(_auth("42"), PrivateChannel("unknown.1"))
        )
        assert result is False
