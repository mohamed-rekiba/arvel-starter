"""WI-007 Mail infrastructure tests — MailFake and WelcomeMail.

Covers Epic 004 Story 2: MailContract + Mailable usage.
"""

from __future__ import annotations

import pytest

from arvel.mail.fakes import MailFake

from app.mail.welcome_mail import WelcomeMail


@pytest.fixture
def mail_fake() -> MailFake:
    return MailFake()


class TestWelcomeMailConstruction:
    def test_for_user_sets_recipient_and_subject(self) -> None:
        mail = WelcomeMail.for_user("alice@test.com", "Alice")
        assert mail.to == ["alice@test.com"]
        assert mail.subject == "Welcome to Arvel"
        assert "Alice" in mail.body

    def test_for_user_includes_name_in_context(self) -> None:
        mail = WelcomeMail.for_user("bob@test.com", "Bob")
        assert mail.context["name"] == "Bob"


class TestMailFakeSendAndAssert:
    @pytest.mark.anyio
    async def test_send_captures_mailable(self, mail_fake: MailFake) -> None:
        mail = WelcomeMail.for_user("test@test.com", "Test")
        await mail_fake.send(mail)
        mail_fake.assert_sent(subject="Welcome to Arvel")

    @pytest.mark.anyio
    async def test_assert_nothing_sent_passes_when_empty(
        self, mail_fake: MailFake
    ) -> None:
        mail_fake.assert_nothing_sent()

    @pytest.mark.anyio
    async def test_assert_sent_to_checks_recipient(self, mail_fake: MailFake) -> None:
        mail = WelcomeMail.for_user("user@test.com", "User")
        await mail_fake.send(mail)
        mail_fake.assert_sent_to("user@test.com")

    @pytest.mark.anyio
    async def test_assert_sent_count_matches(self, mail_fake: MailFake) -> None:
        for i in range(3):
            mail = WelcomeMail.for_user(f"u{i}@test.com", f"User{i}")
            await mail_fake.send(mail)
        mail_fake.assert_sent_count(3)
