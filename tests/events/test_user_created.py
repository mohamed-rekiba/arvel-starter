"""Tests for UserCreated event structure."""

from __future__ import annotations

from app.events.user_created import UserCreated


class TestUserCreatedEvent:
    def test_event_stores_user_id(self):
        event = UserCreated(user_id=1, email="test@test.com", name="Alice")
        assert event.user_id == 1

    def test_event_stores_email(self):
        event = UserCreated(user_id=1, email="test@test.com", name="Alice")
        assert event.email == "test@test.com"

    def test_event_stores_name(self):
        event = UserCreated(user_id=1, email="test@test.com", name="Alice")
        assert event.name == "Alice"
