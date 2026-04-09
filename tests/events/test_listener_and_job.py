"""Tests for SendWelcomeEmailListener, SendWelcomeEmailJob, and WelcomeMail."""

from __future__ import annotations

from app.events.user_created import UserCreated
from app.jobs.send_welcome_email_job import SendWelcomeEmailJob
from app.mail.welcome_mail import WelcomeMail
from app.notifications.welcome_notification import WelcomeNotification


class TestWelcomeMail:
    def test_for_user_creates_mailable_with_correct_fields(self):
        mail = WelcomeMail.for_user("alice@test.com", "Alice")
        assert mail.to == ["alice@test.com"]
        assert mail.subject == "Welcome to Arvel"
        assert "Alice" in mail.body

    def test_class_has_template_attribute(self):
        assert WelcomeMail.template == "welcome.html"


class TestSendWelcomeEmailJob:
    def test_job_stores_payload_fields(self):
        job = SendWelcomeEmailJob(user_id=1, email="bob@test.com", name="Bob")
        assert job.user_id == 1
        assert job.email == "bob@test.com"
        assert job.name == "Bob"

    def test_job_has_retry_config(self):
        job = SendWelcomeEmailJob(user_id=1, email="x@t.com", name="X")
        assert job.max_retries == 2
        assert job.backoff == 10
        assert job.queue_name == "default"

    async def test_job_handle_uses_log_mailer_in_test(self, monkeypatch):
        """In test env (MAIL_DRIVER=log), handle() should complete without error."""
        monkeypatch.setenv("MAIL_DRIVER", "log")
        job = SendWelcomeEmailJob(user_id=42, email="test@t.com", name="Test")
        await job.handle()


class TestWelcomeNotification:
    def test_via_returns_mail_and_database(self):
        notif = WelcomeNotification(name="Alice")
        assert notif.via() == ["mail", "database"]

    def test_to_mail_returns_message_with_name(self):
        notif = WelcomeNotification(name="Bob")
        msg = notif.to_mail(None)
        assert msg.subject == "Welcome to Arvel"
        assert "Bob" in msg.body

    def test_to_database_returns_payload_with_name(self):
        notif = WelcomeNotification(name="Charlie")
        payload = notif.to_database(None)
        assert payload.type == "welcome"
        assert payload.data["name"] == "Charlie"


class TestUserCreatedEventIntegration:
    def test_event_fields_match_listener_expectations(self):
        event = UserCreated(user_id=5, email="e@t.com", name="Eve")
        assert hasattr(event, "user_id")
        assert hasattr(event, "email")
        assert hasattr(event, "name")
