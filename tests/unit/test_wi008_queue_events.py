"""WI-008 Queue and Events tests — Job, Event, Listener, EventDispatcher.

Covers Epic 005: Queue dispatch, domain events, listeners, and fakes.
"""

from __future__ import annotations

import pytest

from arvel.events import EventDispatcher
from arvel.events.fake import EventFake
from arvel.events.listener import Listener
from arvel.queue.fake import QueueFake

from app.events.user_created import UserCreated
from app.jobs.send_welcome_email_job import SendWelcomeEmailJob
from app.listeners.send_welcome_email_listener import SendWelcomeEmailListener


class TestUserCreatedEvent:
    def test_event_carries_user_data(self) -> None:
        event = UserCreated(user_id=1, email="alice@test.com", name="Alice")
        assert event.user_id == 1
        assert event.email == "alice@test.com"
        assert event.name == "Alice"
        assert event.occurred_at is not None

    def test_event_is_frozen(self) -> None:
        event = UserCreated(user_id=1, email="test@test.com", name="Test")
        with pytest.raises(Exception):
            event.user_id = 2  # type: ignore[misc]


class TestSendWelcomeEmailJob:
    def test_job_carries_payload(self) -> None:
        job = SendWelcomeEmailJob(user_id=1, email="alice@test.com", name="Alice")
        assert job.user_id == 1
        assert job.email == "alice@test.com"
        assert job.name == "Alice"
        assert job.max_retries == 2
        assert job.queue_name == "default"


class TestQueueFakeDispatch:
    @pytest.mark.anyio
    async def test_dispatch_captures_job(self) -> None:
        fake = QueueFake()
        job = SendWelcomeEmailJob(user_id=1, email="test@t.com", name="Test")
        await fake.dispatch(job)
        fake.assert_pushed(SendWelcomeEmailJob)

    @pytest.mark.anyio
    async def test_assert_nothing_pushed_when_empty(self) -> None:
        fake = QueueFake()
        fake.assert_nothing_pushed()

    @pytest.mark.anyio
    async def test_assert_pushed_count_matches(self) -> None:
        fake = QueueFake()
        for i in range(3):
            await fake.dispatch(
                SendWelcomeEmailJob(user_id=i, email=f"u{i}@t.com", name=f"U{i}")
            )
        fake.assert_pushed_count(SendWelcomeEmailJob, 3)


class TestEventDispatcherRegistration:
    def test_register_and_list_listeners(self) -> None:
        dispatcher = EventDispatcher()
        dispatcher.register(UserCreated, SendWelcomeEmailListener)
        listeners = dispatcher.listeners_for(UserCreated)
        assert len(listeners) == 1

    @pytest.mark.anyio
    async def test_dispatch_invokes_listener(self) -> None:
        dispatched: list[UserCreated] = []

        class RecordingListener(Listener):
            async def handle(self, event: UserCreated) -> None:
                dispatched.append(event)

        dispatcher = EventDispatcher()
        dispatcher.register(UserCreated, RecordingListener)
        event = UserCreated(user_id=42, email="eve@test.com", name="Eve")
        await dispatcher.dispatch(event)
        assert len(dispatched) == 1
        assert dispatched[0].user_id == 42


class TestEventFakeAssertions:
    @pytest.mark.anyio
    async def test_assert_dispatched_passes(self) -> None:
        fake = EventFake()
        event = UserCreated(user_id=1, email="a@t.com", name="A")
        await fake.dispatch(event)
        fake.assert_dispatched(UserCreated)

    @pytest.mark.anyio
    async def test_assert_not_dispatched_passes_when_absent(self) -> None:
        fake = EventFake()
        fake.assert_not_dispatched(UserCreated)

    @pytest.mark.anyio
    async def test_assert_nothing_dispatched_passes_when_empty(self) -> None:
        fake = EventFake()
        fake.assert_nothing_dispatched()

    @pytest.mark.anyio
    async def test_assert_dispatched_count_matches(self) -> None:
        fake = EventFake()
        for i in range(5):
            await fake.dispatch(
                UserCreated(user_id=i, email=f"u{i}@t.com", name=f"U{i}")
            )
        fake.assert_dispatched_count(UserCreated, 5)
