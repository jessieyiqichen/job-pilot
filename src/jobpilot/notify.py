"""Email delivery for daily digests via SMTP (Gmail by default).

Credentials are read from the environment only (config.SMTP_*), never
hardcoded. Use a Gmail *App Password*, not your login password.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate

from jobpilot import config

logger = logging.getLogger(__name__)


class EmailNotConfigured(RuntimeError):
    """Raised when SMTP credentials are missing."""


def is_configured() -> bool:
    """True when the minimum SMTP credentials are present."""
    return bool(config.SMTP_USER and config.SMTP_PASSWORD)


def send_email(subject: str, body: str, *, to: str | None = None) -> str:
    """Send a plain-text email via SMTP. Returns the recipient address.

    Raises:
        EmailNotConfigured: when SMTP_USER / SMTP_PASSWORD are not set.
        smtplib.SMTPException: on transport/auth failure.
    """
    if not is_configured():
        raise EmailNotConfigured(
            "缺少 SMTP 凭证：请在 .env 设置 JOBPILOT_SMTP_USER 和 "
            "JOBPILOT_SMTP_PASSWORD（Gmail 应用专用密码）"
        )

    recipient = to or config.SMTP_TO or config.SMTP_USER

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config.SMTP_USER
    msg["To"] = recipient
    msg["Date"] = formatdate(localtime=True)

    logger.info("Sending email to %s via %s:%s", recipient, config.SMTP_HOST, config.SMTP_PORT)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.sendmail(config.SMTP_USER, [recipient], msg.as_string())

    return recipient
