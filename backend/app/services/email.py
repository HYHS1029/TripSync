"""SMTP delivery only. Tokens and provider errors must never be logged."""
from email.message import EmailMessage
import smtplib
import ssl

from app.core.config import get_settings


class EmailDeliveryError(Exception):
    pass


def send_email(recipient: str, subject: str, text: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        raise EmailDeliveryError("Email delivery is not configured")
    message = EmailMessage()
    message["From"] = f"TripSync <{settings.smtp_from_email}>"
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text)
    try:
        connection = (
            smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=5, context=ssl.create_default_context())
            if settings.smtp_security == "ssl"
            else smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5)
        )
        with connection as smtp:
            if settings.smtp_security == "starttls":
                smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        raise EmailDeliveryError("Unable to send email") from None


def send_verification_email(recipient: str, username: str, token: str) -> None:
    settings = get_settings()
    # Fragments do not enter HTTP access logs or Referer headers.
    link = f"{settings.frontend_url}/verify-email#{token}"
    send_email(recipient, "驗證你的 TripSync 電子郵件", (
        f"你好，{username}：\n\n"
        f"請使用提出申請的 TripSync 帳號登入，再開啟以下連結確認綁定此信箱：\n{link}\n\n"
        f"連結將於 {settings.email_verification_expire_minutes} 分鐘後失效，且只能使用一次。\n"
        "若你沒有提出這項申請，請忽略這封信，不要替他人確認。\n"
    ))
