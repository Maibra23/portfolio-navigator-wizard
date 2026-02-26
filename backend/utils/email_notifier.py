#!/usr/bin/env python3
"""
Email notifier utility (single recipient via SMTP, Gmail-friendly).

Design goal:
- ALL notifications go to the same recipient (TTL_NOTIFICATION_EMAIL) via SMTP.
- Uses smtplib (stdlib); no per-message recipient overrides.
- For Gmail: use smtp.gmail.com:587 with an app password (SMTP_PASSWORD).
"""

from __future__ import annotations

import logging
import os
import re
import smtplib
import time
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

_LAST_SENT: dict[str, float] = {}

# Simple validation: allow only typical email format to reduce header injection risk
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
_MAX_EMAIL_LEN = 254


@dataclass(frozen=True)
class NotificationMessage:
    title: str
    message: str
    severity: str = "INFO"  # INFO, WARNING, CRITICAL, SUCCESS, EXPIRED
    fields: dict[str, str] | None = None


def _enabled() -> bool:
    return os.getenv("TTL_EMAIL_NOTIFICATIONS", "false").lower() == "true"


def _to_email() -> str | None:
    raw = os.getenv("TTL_NOTIFICATION_EMAIL") or ""
    s = (raw or "").strip()
    if not s or len(s) > _MAX_EMAIL_LEN:
        return None
    if not _EMAIL_RE.match(s):
        return None
    return s


def _smtp_host() -> str:
    return os.getenv("SMTP_HOST", "smtp.gmail.com").strip()


def _smtp_port() -> int:
    try:
        return int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        return 587


def _smtp_user() -> str | None:
    return (os.getenv("SMTP_USER") or "").strip() or None


def _smtp_password() -> str | None:
    # Support both SMTP_PASSWORD and GMAIL_APP_PASSWORD for clarity in docs
    return (os.getenv("SMTP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD") or "").strip() or None


def _emoji(severity: str) -> str:
    return {
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "CRITICAL": "🚨",
        "SUCCESS": "✅",
        "EXPIRED": "❌",
    }.get((severity or "").upper(), "🔔")


def _build_plain_body(msg: NotificationMessage) -> str:
    lines = [
        f"{_emoji(msg.severity)} {msg.title}",
        "",
        msg.message,
    ]
    if msg.fields:
        lines.append("")
        for k, v in (msg.fields or {}).items():
            lines.append(f"{k}: {v}")
    return "\n".join(lines)


def _build_html_body(msg: NotificationMessage) -> str:
    severity = (msg.severity or "INFO").upper()
    fields_html = ""
    if msg.fields:
        rows = "".join(
            f"<tr><td><strong>{k}</strong></td><td>{_escape_html(str(v))}</td></tr>"
            for k, v in msg.fields.items()
        )
        fields_html = f"<table>{rows}</table>"
    body = f"""
<html><body>
<h2>{_emoji(msg.severity)} {msg.title}</h2>
<p>{_escape_html(msg.message)}</p>
{fields_html}
<p><small>Severity: {severity}</small></p>
</body></html>
"""
    return body.strip()


def _escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def send_notification(
    msg: NotificationMessage,
    throttle_key: str | None = None,
    min_interval_seconds: int = 0,
) -> None:
    """
    Send an email notification via SMTP (TLS on port 587).

    throttle_key + min_interval_seconds:
      - prevents spamming the same alert repeatedly
      - in-memory only (resets on process restart)
    """
    try:
        if not _enabled():
            return

        to_addr = _to_email()
        if not to_addr:
            logger.debug("TTL_NOTIFICATION_EMAIL not configured or invalid")
            return

        user = _smtp_user()
        password = _smtp_password()
        if not user or not password:
            logger.debug("SMTP_USER / SMTP_PASSWORD not configured")
            return

        if throttle_key and min_interval_seconds > 0:
            now = time.time()
            last = _LAST_SENT.get(throttle_key, 0.0)
            if (now - last) < min_interval_seconds:
                return
            _LAST_SENT[throttle_key] = now

        host = _smtp_host()
        port = _smtp_port()

        mime = MIMEMultipart("alternative")
        mime["Subject"] = f"[{msg.severity}] {msg.title}"
        mime["From"] = f"Portfolio-wizard App <{user}>"
        mime["To"] = to_addr

        mime.attach(MIMEText(_build_plain_body(msg), "plain", "utf-8"))
        mime.attach(MIMEText(_build_html_body(msg), "html", "utf-8"))

        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.sendmail(user, [to_addr], mime.as_string())

        logger.debug("Email notification sent")
    except Exception as e:
        logger.debug("Email send failed (non-fatal): %s", type(e).__name__)
