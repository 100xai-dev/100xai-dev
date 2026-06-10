"""Transactional email delivery.

Two backends are supported, selected via ``settings.email_backend``:
- ``console`` (default): logs the message + any link. Zero-config for local dev.
- ``smtp``: sends via SMTP using stdlib ``smtplib`` (works with any provider).

Send calls are synchronous and lightweight; callers should invoke them from a
FastAPI ``BackgroundTasks`` so the request is not blocked on network I/O.
"""

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger(__name__)


def _deliver(to_email: str, subject: str, body: str) -> None:
    settings = get_settings()

    if settings.email_backend == "console" or not settings.smtp_host:
        logger.info(
            "[email:console] to=%s subject=%s\n%s",
            to_email,
            subject,
            body,
        )
        return

    msg = EmailMessage()
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        logger.info("Sent email to %s (subject=%s)", to_email, subject)
    except Exception:  # noqa: BLE001 - never let email failures break the request flow
        logger.exception("Failed to send email to %s (subject=%s)", to_email, subject)


def build_verification_link(token: str) -> str:
    base = get_settings().frontend_url.rstrip("/")
    return f"{base}/verify-email?token={token}"


def send_verification_email(to_email: str, token: str) -> None:
    link = build_verification_link(token)
    body = (
        "Welcome to 100xAI!\n\n"
        "Please confirm your email address by opening the link below:\n\n"
        f"{link}\n\n"
        "This link expires in "
        f"{get_settings().email_verification_expiry_hours} hours.\n\n"
        "If you did not create an account, you can ignore this email."
    )
    _deliver(to_email, "Verify your 100xAI email", body)


def send_welcome_email(to_email: str) -> None:
    body = (
        "Your email is verified — welcome to 100xAI!\n\n"
        "You can now sign in and start building."
    )
    _deliver(to_email, "Welcome to 100xAI", body)
