"""
Email sending for auth flows. SMTP is optional; without it we log the payload.
"""
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.core.settings import settings

logger = logging.getLogger(__name__)


def send_email(to_address: str, subject: str, body: str) -> bool:
    """Send a plaintext email. Returns True if handed to SMTP, False if logged only."""
    if not settings.smtp_host:
        logger.info("[EMAIL] SMTP not configured. to=%s subject=%s\n%s", to_address, subject, body)
        return False

    from_addr = settings.smtp_from or settings.smtp_user or "noreply@localhost"
    message = EmailMessage()
    message["From"] = from_addr
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
        logger.info("[EMAIL] Sent to %s (%s)", to_address, subject)
        return True
    except Exception as exc:
        logger.error("[EMAIL] Failed to send to %s: %s", to_address, exc)
        raise


def send_password_reset_email(to_address: str, reset_url: str) -> Optional[bool]:
    body = (
        "Bạn vừa yêu cầu đặt lại mật khẩu cho AIRC Internal Chatbot.\n\n"
        f"Mở liên kết sau (hết hạn sau {settings.password_reset_expire_minutes} phút):\n"
        f"{reset_url}\n\n"
        "Nếu bạn không yêu cầu, hãy bỏ qua email này."
    )
    return send_email(to_address, "Đặt lại mật khẩu AIRC Chatbot", body)
