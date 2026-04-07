"""WelcomeNotification — multi-channel notification for new users."""

from __future__ import annotations

from typing import Any

from arvel.notifications.notification import (
    DatabasePayload,
    MailMessage,
    Notification,
)


class WelcomeNotification(Notification):
    """Sent to a user after registration via mail and database channels."""

    def __init__(self, name: str) -> None:
        self._name = name

    def via(self) -> list[str]:
        return ["mail", "database"]

    def to_mail(self, notifiable: Any) -> MailMessage:
        return MailMessage(
            subject="Welcome to Arvel",
            body=f"Hello {self._name}, welcome to the Arvel framework!",
        )

    def to_database(self, notifiable: Any) -> DatabasePayload:
        return DatabasePayload(
            type="welcome",
            data={"name": self._name, "message": "Welcome to Arvel!"},
        )
