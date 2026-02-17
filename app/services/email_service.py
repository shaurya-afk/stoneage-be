"""
Send extraction Excel to user email via SMTP.

Configure in .env:
  SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD,
  SMTP_USE_TLS (default true), MAIL_FROM (optional, defaults to SMTP_USER).
"""
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


def _is_email_configured() -> bool:
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    return bool(host and user and password)


def send_excel_to_user(
    to_email: str,
    excel_path: str | Path,
    subject: str | None = None,
    body: str | None = None,
) -> tuple[bool, str]:
    """
    Send the generated Excel file to the given email address.
    Returns (True, "sent") if sent successfully,
    (False, reason) if not configured or send fails.
    """
    if not _is_email_configured():
        return False, "smtp_not_configured"

    path = Path(excel_path)
    if not path.exists():
        return False, "file_not_found"

    subject = subject or "Your extraction report - Stone Age"
    body = body or "Please find your extraction report attached."

    from_email = os.getenv("MAIL_FROM") or os.getenv("SMTP_USER")
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
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                server.login(user, password)
                server.sendmail(from_email, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(host, port) as server:
                server.login(user, password)
                server.sendmail(from_email, [to_email], msg.as_string())
        return True, "sent"
    except Exception as e:
        return False, f"send_failed: {e!s}"
