"""WelcomeMail — sent to new users after registration."""

from __future__ import annotations

from arvel.mail.mailable import Mailable


class WelcomeMail(Mailable):
    """Welcome email dispatched when a new user is created.

    Uses the log driver in dev/test — no real SMTP needed.
    """

    subject: str = "Welcome to Arvel"
    template: str = "welcome.html"

    @classmethod
    def for_user(cls, email: str, name: str) -> WelcomeMail:
        return cls(
            to=[email],
            subject="Welcome to Arvel",
            body=f"Hello {name}, welcome to the Arvel framework!",
            context={"name": name},
        )
