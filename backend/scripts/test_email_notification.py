#!/usr/bin/env python3
"""
One-off test script for email notification delivery.
Sets test recipient, loads SMTP from .env, sends one message, reports success/failure.
Run from backend: python scripts/test_email_notification.py
Delete this script after verifying delivery.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env before reading env vars
def _load_dotenv():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(backend_dir, ".env")
    if not os.path.isfile(env_path):
        return False
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        return True
    except ImportError:
        return False


def _progress(step: int, total: int, msg: str) -> None:
    print(f"  [{step}/{total}] {msg}", flush=True)


def main() -> int:
    total_steps = 4
    _progress(1, total_steps, "Loading .env ...")
    if not _load_dotenv():
        print("FAIL: Could not load .env (file missing or python-dotenv not installed).")
        return 1

    # Use test recipient as specified in plan
    os.environ["TTL_EMAIL_NOTIFICATIONS"] = "true"
    os.environ["TTL_NOTIFICATION_EMAIL"] = "stay.away202@gmail.com"

    to_addr = os.environ.get("TTL_NOTIFICATION_EMAIL", "").strip()
    user = (os.environ.get("SMTP_USER") or "").strip()
    password = (os.environ.get("SMTP_PASSWORD") or os.environ.get("GMAIL_APP_PASSWORD") or "").strip()
    host = (os.environ.get("SMTP_HOST") or "smtp.gmail.com").strip()
    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError:
        port = 587

    if not to_addr:
        print("FAIL: TTL_NOTIFICATION_EMAIL is not set.")
        return 1
    if not user or not password:
        print("FAIL: SMTP_USER or SMTP_PASSWORD (or GMAIL_APP_PASSWORD) not set in .env.")
        print("  Set them in backend/.env and run this script again.")
        return 1

    _progress(2, total_steps, "Preparing test message ...")
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import smtplib

    subject = "[INFO] Portfolio Wizard – Email test"
    body_plain = "This is a test email from the Portfolio Navigator Wizard email notification test script. If you received this, SMTP is configured correctly."

    mime = MIMEMultipart("alternative")
    mime["Subject"] = subject
    mime["From"] = user
    mime["To"] = to_addr
    mime.attach(MIMEText(body_plain, "plain", "utf-8"))

    _progress(3, total_steps, "Sending test email ...")
    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.sendmail(user, [to_addr], mime.as_string())
    except Exception as e:
        print(f"FAIL: Email send failed: {type(e).__name__}: {e}")
        return 1

    _progress(4, total_steps, "Done.")
    print(f"SUCCESS: Test email sent to {to_addr}. Check your inbox (and spam folder).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
