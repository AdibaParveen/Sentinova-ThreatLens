from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import get_settings

settings = get_settings()


def send_email(to_addr: str, subject: str, html: str, text: str | None = None) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to_addr
    msg.set_content(text or "Please view this message in an HTML client.")
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_tls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


def verification_email(to_addr: str, name: str, link: str) -> None:
    send_email(
        to_addr,
        "Verify your ThreatLens account",
        f"""
        <div style="font-family:Segoe UI,sans-serif;background:#0b1220;color:#e8eefc;padding:32px">
          <h2>ThreatLens</h2>
          <p>Hello {name},</p>
          <p>Confirm your email to activate your SOC account. This link expires in 24 hours.</p>
          <p><a href="{link}" style="background:#2f6fed;color:white;padding:10px 16px;border-radius:6px;text-decoration:none">Verify email</a></p>
          <p style="color:#8aa0c8;font-size:12px">If you did not register, ignore this message.</p>
        </div>
        """,
    )


def reset_email(to_addr: str, name: str, link: str) -> None:
    send_email(
        to_addr,
        "Reset your ThreatLens password",
        f"""
        <div style="font-family:Segoe UI,sans-serif;background:#0b1220;color:#e8eefc;padding:32px">
          <h2>ThreatLens</h2>
          <p>Hello {name},</p>
          <p>Use the button below to choose a new password. This link expires in 1 hour.</p>
          <p><a href="{link}" style="background:#2f6fed;color:white;padding:10px 16px;border-radius:6px;text-decoration:none">Reset password</a></p>
        </div>
        """,
    )
