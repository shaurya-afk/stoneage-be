"""
Send extraction Excel to user email.

Supports two backends (use one):
  - Resend (recommended on Render): RESEND_API_KEY, MAIL_FROM (e.g. onboarding@resend.dev or your verified domain).
  - SMTP (e.g. Gmail): SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_TLS, MAIL_FROM.
"""
import base64
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests


def _is_resend_configured() -> bool:
    return bool(os.getenv("RESEND_API_KEY"))


def _is_smtp_configured() -> bool:
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    return bool(host and user and password)


def _is_email_configured() -> bool:
    return _is_resend_configured() or _is_smtp_configured()


def _send_via_resend(to_email: str, from_email: str, subject: str, body: str, path: Path) -> tuple[bool, str]:
    """Send via Resend API (HTTPS). Works on Render where SMTP is often blocked."""
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        return False, "resend_not_configured"
    with open(path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode("ascii")
    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "text": body,
        "attachments": [{"filename": path.name, "content": content_b64}],
    }
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if r.status_code == 200:
            return True, "sent"
        return False, f"resend_failed: {r.status_code} {r.text[:200]}"
    except Exception as e:
        return False, f"send_failed: {e!s}"


def send_excel_to_user(
    to_email: str,
    excel_path: str | Path,
    subject: str | None = None,
    body: str | None = None,
) -> tuple[bool, str]:
    """
    Send the generated Excel file to the given email address.
    Uses Resend if RESEND_API_KEY is set (recommended on Render), else SMTP.
    Returns (True, "sent") if sent successfully,
    (False, reason) if not configured or send fails.
    """
    if not _is_email_configured():
        return False, "email_not_configured"

    path = Path(excel_path)
    if not path.exists():
        return False, "file_not_found"

    subject = subject or "Your extraction report - Stone Age"
    body = body or "Please find your extraction report attached."
    from_email = os.getenv("MAIL_FROM") or os.getenv("SMTP_USER") or "onboarding@resend.dev"

    if _is_resend_configured():
        return _send_via_resend(to_email, from_email, subject, body, path)

    # SMTP (often blocked on Render)
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain"))

    with open(path, "rb") as f:
        attachment = MIMEApplication(f.read(), _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=path.name,
    )
    msg.attach(attachment)

    try:
        if use_tls:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.starttls()
                server.login(user, password)
                server.sendmail(from_email, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.login(user, password)
                server.sendmail(from_email, [to_email], msg.as_string())
        return True, "sent"
    except Exception as e:
        return False, f"send_failed: {e!s}"


def send_text_email(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    """
    Send a plain-text email (no attachments).
    Uses Resend if RESEND_API_KEY is set, else SMTP.
    Returns (True, "sent") on success, (False, reason) otherwise.
    """
    if not _is_email_configured():
        return False, "email_not_configured"

    from_email = os.getenv("MAIL_FROM") or os.getenv("SMTP_USER") or "onboarding@resend.dev"

    if _is_resend_configured():
        return _send_via_resend_text(to_email, from_email, subject, body)

    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")

    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    try:
        if use_tls:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.starttls()
                server.login(user, password)
                server.sendmail(from_email, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.login(user, password)
                server.sendmail(from_email, [to_email], msg.as_string())
        return True, "sent"
    except Exception as e:
        return False, f"send_failed: {e!s}"
