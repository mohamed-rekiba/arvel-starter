"""Tests for UserObserver — email normalization, event dispatch, search indexing."""

from __future__ import annotations

from typing import Any

from arvel.broadcasting.channels import Channel
from arvel.broadcasting.contracts import BroadcastContract
from arvel.events.dispatcher import EventDispatcher
from arvel.events.event import Event
from arvel.search.contracts import SearchEngine, SearchResult

from app.events.user_created import UserCreated
from app.models.user import User
from app.observers.user_observer import UserObserver


class _SpySearchEngine(SearchEngine):
    """Captures upsert calls for assertion."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[dict[str, Any]]]] = []

    async def upsert_documents(
        self, index: str, documents: list[dict[str, Any]], primary_key: str = "id"
    ) -> None:
        self.calls.append((index, documents))

    async def remove_documents(self, index: str, ids: list[str | int]) -> None:
        pass

    async def search(
        self,
        index: str,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResult:
        return SearchResult(hits=[], total=0)

    async def flush(self, index: str) -> None:
        pass

    async def create_index(self, index: str, *, primary_key: str = "id") -> None:
        pass

    async def delete_index(self, index: str) -> None:
        pass


class _SpyEventDispatcher(EventDispatcher):
    """Captures dispatched events for assertion."""

    def __init__(self) -> None:
        super().__init__()
        self.events: list[Event] = []

    async def dispatch(self, event: Event) -> None:
        self.events.append(event)
        await super().dispatch(event)


class _SpyBroadcaster(BroadcastContract):
    """Captures broadcast calls for assertion."""

    def __init__(self) -> None:
        self.broadcasts: list[tuple[list[Channel], str, dict[str, Any]]] = []

    async def broadcast(
        self,
        channels: list[Channel],
        event: str,
        data: dict[str, Any],
    ) -> None:
        self.broadcasts.append((channels, event, data))


class TestUserObserverCreating:
    async def test_creating_normalizes_email_to_lowercase(self):
        observer = UserObserver()
        user = User(name="Alice", email="  Alice@EXAMPLE.COM  ", password="hashed")
        result = await observer.creating(user)
        assert result is True
        assert user.email == "alice@example.com"

    async def test_creating_strips_whitespace(self):
        observer = UserObserver()
        user = User(name="Bob", email="  bob@test.com  ", password="hashed")
        await observer.creating(user)
        assert user.email == "bob@test.com"


class TestUserObserverUpdating:
    async def test_updating_normalizes_email(self):
        observer = UserObserver()
        user = User(name="Charlie", email="  Charlie@Test.COM  ", password="hashed")
        result = await observer.updating(user)
        assert result is True
        assert user.email == "charlie@test.com"


class TestUserObserverUpdated:
    async def test_updated_without_services_does_not_raise(self):
        observer = UserObserver()
        user = User(name="UpdateNoSvc", email="upd@test.com", password="hashed")
        user.id = 10
        await observer.updated(user)

    async def test_updated_re_indexes_search(self):
        search = _SpySearchEngine()
        observer = UserObserver(search_engine=search)
        user = User(name="UpdateSearch", email="updsearch@test.com", password="hashed")
        user.id = 11
        await observer.updated(user)
        assert len(search.calls) == 1
        assert search.calls[0][0] == User.search_index_name()


class TestUserObserverCreatedSideEffects:
    async def test_created_without_services_does_not_raise(self):
        observer = UserObserver()
        user = User(name="Dave", email="dave@test.com", password="hashed")
        user.id = 1
        await observer.created(user)

    async def test_created_calls_search_engine_upsert(self):
        search = _SpySearchEngine()
        observer = UserObserver(search_engine=search)
        user = User(name="Eve", email="eve@test.com", password="hashed")
        user.id = 2
        await observer.created(user)
        assert len(search.calls) == 1
        assert search.calls[0][0] == User.search_index_name()

    async def test_created_dispatches_user_created_event(self):
        dispatcher = _SpyEventDispatcher()
        observer = UserObserver(event_dispatcher=dispatcher)
        user = User(name="Frank", email="frank@test.com", password="hashed")
        user.id = 3
        await observer.created(user)
        assert len(dispatcher.events) == 1
        event = dispatcher.events[0]
        assert isinstance(event, UserCreated)
        assert event.user_id == 3
        assert event.email == "frank@test.com"

    async def test_created_broadcasts_user_created(self):
        broadcaster = _SpyBroadcaster()
        observer = UserObserver(broadcaster=broadcaster)
        user = User(name="Grace", email="grace@test.com", password="hashed")
        user.id = 4
        await observer.created(user)
        assert len(broadcaster.broadcasts) == 1
        assert broadcaster.broadcasts[0][1] == "user.created"
