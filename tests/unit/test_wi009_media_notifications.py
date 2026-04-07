"""WI-009 Media and Notifications tests — MediaFake, NotificationFake.

Covers Epic 006: Media library usage, notification dispatch via
mail and database channels, and the WelcomeNotification.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from arvel.media.fakes import MediaFake
from arvel.media.types import MediaCollection
from arvel.notifications.fakes import NotificationFake

from app.notifications.welcome_notification import WelcomeNotification


class _FakeNotifiable:
    """Minimal notifiable object for testing notification channels."""

    def __init__(self, *, user_id: int, email: str, name: str) -> None:
        self.id = user_id
        self.email = email
        self.name = name


class _FakeModel:
    """Minimal model-like object for media testing."""

    def __init__(self, model_id: int) -> None:
        self.id = model_id


class TestMediaFakeAddAndRetrieve:
    @pytest.mark.anyio
    async def test_add_stores_and_get_media_retrieves(self) -> None:
        fake = MediaFake()
        model = _FakeModel(1)
        media = await fake.add(model, b"image-data", "photo.png", collection="avatars")
        assert media.collection == "avatars"
        assert media.original_filename == "photo.png"
        assert media.size == len(b"image-data")

        items = await fake.get_media(model, "avatars")
        assert len(items) == 1
        assert items[0].id == media.id

    @pytest.mark.anyio
    async def test_get_first_url_returns_path(self) -> None:
        fake = MediaFake()
        model = _FakeModel(1)
        await fake.add(model, b"data", "file.png", collection="profile_images")
        url = await fake.get_first_url(model, "profile_images")
        assert url is not None
        assert "fake-storage" in url

    @pytest.mark.anyio
    async def test_get_first_url_returns_none_when_empty(self) -> None:
        fake = MediaFake()
        model = _FakeModel(1)
        url = await fake.get_first_url(model, "empty")
        assert url is None


class TestMediaFakeCollectionFiltering:
    @pytest.mark.anyio
    async def test_get_media_filters_by_collection(self) -> None:
        fake = MediaFake()
        model = _FakeModel(1)
        await fake.add(model, b"a", "a.png", collection="avatars")
        await fake.add(model, b"b", "b.pdf", collection="documents")

        avatars = await fake.get_media(model, "avatars")
        assert len(avatars) == 1
        assert avatars[0].collection == "avatars"

        docs = await fake.get_media(model, "documents")
        assert len(docs) == 1
        assert docs[0].collection == "documents"


class TestMediaFakeValidation:
    @pytest.mark.anyio
    async def test_invalid_mime_type_raises(self) -> None:
        fake = MediaFake()
        model = _FakeModel(1)
        col = MediaCollection(
            name="images",
            allowed_mime_types=["image/png", "image/jpeg"],
        )
        fake.register_collection(type(model), col)

        from arvel.media.exceptions import MediaValidationError

        with pytest.raises(MediaValidationError):
            await fake.add(
                model,
                b"data",
                "file.txt",
                collection="images",
                content_type="text/plain",
            )

    @pytest.mark.anyio
    async def test_oversized_file_raises(self) -> None:
        fake = MediaFake()
        model = _FakeModel(1)
        col = MediaCollection(name="limited", max_file_size=10)
        fake.register_collection(type(model), col)

        from arvel.media.exceptions import MediaValidationError

        with pytest.raises(MediaValidationError):
            await fake.add(model, b"x" * 100, "big.bin", collection="limited")


class TestMediaFakeDeleteAll:
    @pytest.mark.anyio
    async def test_delete_all_removes_media(self) -> None:
        fake = MediaFake()
        model = _FakeModel(1)
        await fake.add(model, b"a", "a.png", collection="avatars")
        await fake.add(model, b"b", "b.png", collection="avatars")
        count = await fake.delete_all(model, "avatars")
        assert count == 2
        assert await fake.get_media(model, "avatars") == []


class TestMediaFakeAssertions:
    @pytest.mark.anyio
    async def test_assert_added_passes_after_add(self) -> None:
        fake = MediaFake()
        model = _FakeModel(1)
        await fake.add(model, b"data", "file.png", collection="uploads")
        fake.assert_added("uploads")

    @pytest.mark.anyio
    async def test_assert_nothing_added_passes_when_empty(self) -> None:
        fake = MediaFake()
        fake.assert_nothing_added()

    @pytest.mark.anyio
    async def test_assert_added_count(self) -> None:
        fake = MediaFake()
        model = _FakeModel(1)
        await fake.add(model, b"1", "1.png")
        await fake.add(model, b"2", "2.png")
        fake.assert_added_count(2)


class TestWelcomeNotificationConstruction:
    def test_via_includes_mail_and_database(self) -> None:
        n = WelcomeNotification(name="Alice")
        assert "mail" in n.via()
        assert "database" in n.via()

    def test_to_mail_builds_message(self) -> None:
        n = WelcomeNotification(name="Bob")
        user = _FakeNotifiable(user_id=1, email="bob@t.com", name="Bob")
        msg = n.to_mail(user)
        assert msg.subject == "Welcome to Arvel"
        assert "Bob" in msg.body

    def test_to_database_builds_payload(self) -> None:
        n = WelcomeNotification(name="Charlie")
        user = _FakeNotifiable(user_id=2, email="c@t.com", name="Charlie")
        payload = n.to_database(user)
        assert payload.type == "welcome"
        assert payload.data["name"] == "Charlie"


class TestNotificationFakeAssertions:
    @pytest.mark.anyio
    async def test_assert_sent_to_passes(self) -> None:
        fake = NotificationFake()
        user = _FakeNotifiable(user_id=1, email="test@t.com", name="Test")
        await fake.send(user, WelcomeNotification(name="Test"))
        fake.assert_sent_to(user, WelcomeNotification)

    @pytest.mark.anyio
    async def test_assert_nothing_sent_passes_when_empty(self) -> None:
        fake = NotificationFake()
        fake.assert_nothing_sent()

    @pytest.mark.anyio
    async def test_assert_sent_type_passes(self) -> None:
        fake = NotificationFake()
        user = _FakeNotifiable(user_id=1, email="a@t.com", name="A")
        await fake.send(user, WelcomeNotification(name="A"))
        fake.assert_sent_type(WelcomeNotification)


class TestNotifyEndpointIntegration:
    @pytest.fixture
    def client(self) -> TestClient:
        base_path = Path(__file__).resolve().parents[2]
        app = asyncio.run(
            __import__(
                "arvel.foundation.application", fromlist=["Application"]
            ).Application.create(base_path, testing=True)
        )
        return TestClient(app.asgi_app())

    def test_notify_dispatches_via_mail_channel(self, client: TestClient) -> None:
        response = client.post("/api/users/1/notify")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "sent"
        assert body["channel"] == "mail"

    def test_notify_for_nonexistent_user_returns_404(self, client: TestClient) -> None:
        response = client.post("/api/users/99999/notify")
        assert response.status_code == 404


class TestStorageEndpointIntegration:
    @pytest.fixture
    def client(self) -> TestClient:
        import base64

        self._test_content = base64.b64encode(b"test file content").decode()
        base_path = Path(__file__).resolve().parents[2]
        app = asyncio.run(
            __import__(
                "arvel.foundation.application", fromlist=["Application"]
            ).Application.create(base_path, testing=True)
        )
        return TestClient(app.asgi_app())

    def test_storage_put_and_info_roundtrip(self, client: TestClient) -> None:
        put_resp = client.post(
            "/api/infra/storage",
            json={
                "path": "test/demo.txt",
                "content_base64": self._test_content,
                "content_type": "text/plain",
            },
        )
        assert put_resp.status_code == 201
        body = put_resp.json()
        assert body["action"] == "stored"
        assert body["url"] is not None

        info_resp = client.get("/api/infra/storage/test/demo.txt")
        assert info_resp.status_code == 200
        assert info_resp.json()["exists"] is True

    def test_storage_delete(self, client: TestClient) -> None:
        client.post(
            "/api/infra/storage",
            json={
                "path": "test/to-delete.txt",
                "content_base64": self._test_content,
            },
        )
        del_resp = client.delete("/api/infra/storage/test/to-delete.txt")
        assert del_resp.status_code == 200
        assert del_resp.json()["action"] == "deleted"
