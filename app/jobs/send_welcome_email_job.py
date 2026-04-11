"""SendWelcomeEmailJob — queued background job that sends a welcome email.

Jobs run in worker processes without the app DI container, so the mailer
is built from ``MailSettings`` (env vars).  This mirrors the framework's
``InfrastructureProvider._make_mail`` factory.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.mail.welcome_mail import WelcomeMail
from arvel.mail.config import MailSettings
from arvel.queue import Job

if TYPE_CHECKING:
    from arvel.mail.contracts import MailContract

logger = logging.getLogger(__name__)


def _create_mailer() -> MailContract:
    """Build a mailer from environment config.

    Mirrors ``arvel.infra.provider._make_mail`` — kept here because jobs
    execute outside the app container lifecycle.
    """
    settings = MailSettings()
    if settings.driver == "smtp":
        from arvel.mail.drivers.smtp_driver import SmtpMailer

        return SmtpMailer(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password.get_secret_value(),
            use_tls=settings.smtp_use_tls,
            from_address=settings.from_address,
            from_name=settings.from_name,
            template_dir=settings.template_dir,
        )
    if settings.driver == "null":
        from arvel.mail.drivers.null_driver import NullMailer

        return NullMailer()
    from arvel.mail.drivers.log_driver import LogMailer

    return LogMailer()


class SendWelcomeEmailJob(Job):
    """Sends a welcome email to a newly registered user.

    Dispatched from the user creation flow. Uses ``MailContract``
    (log driver in dev/test) to deliver the ``WelcomeMail``.

    The job payload intentionally excludes the raw password —
    only ``user_id`` and ``email`` are serialised.
    """

    user_id: int
    email: str
    name: str

    max_retries: int = 2
    backoff: int = 10
    queue_name: str = "default"

    async def handle(self) -> None:
        mailer = _create_mailer()
        mail = WelcomeMail.for_user(self.email, self.name)
        await mailer.send(mail)
        logger.info(
            "welcome_email_sent user_id=%s email=%s",
            self.user_id,
            self.email,
        )

    async def on_failure(self, error: Exception) -> None:
        logger.error(
            "welcome_email_failed user_id=%s error=%s",
            self.user_id,
            error,
        )
