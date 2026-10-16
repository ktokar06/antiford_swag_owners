import logging
import smtplib
from email.message import EmailMessage

from core.config import settings

log = logging.getLogger(__name__)


def _send(to: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.smtp_user:
        log.warning("SMTP не настроен, письмо не отправлено: %s", to)
        return
    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


def send_reset_email(email: str, token: str) -> None:
    link = f"{settings.frontend_url}/reset-password?token={token}"
    _send(
        email,
        "Сброс пароля — Антифрод",
        f"Для сброса пароля перейдите по ссылке:\n\n{link}\n\nСсылка действует {settings.reset_token_ttl_minutes} минут.",
    )